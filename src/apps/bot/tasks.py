from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.exceptions import TelegramNetworkError
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import BufferedInputFile
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from taskiq import Context
from taskiq import TaskiqDepends

from apps.worker.app import broker
from core import domains
from core import repos
from core import services
from infra.agents.job_parser import JobParserAgent
from infra.bot.template import TelegramTemplate
from infra.logger.utils import get_logger
from utils.extractors import TextExtractorFactory
from utils.storages.impl.base import AsyncStorage
from utils.transactions.manager import AsyncTransactionManager

logger = get_logger(__name__)

_taskiq_context: Context = TaskiqDepends()  # type: ignore[assignment]


@broker.task()
@inject
async def send_tg_bot_message(
    tg_id: int,
    message: str,
    protect_content: bool | None = None,
    disable_web_page_preview: bool = False,
    disable_notification: bool = False,
    timeout: int | None = None,
    parse_mode: str | None = "HTML",
    tg_bot: Bot = Provide["tg_bot_client"],
) -> None:
    try:
        await tg_bot.send_message(
            tg_id,
            message,
            protect_content=protect_content,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            parse_mode=parse_mode,
            request_timeout=timeout,
        )
    except TelegramNetworkError as err:
        logger.error("Cannot send message due to network error.")
        logger.exception(err)
        raise err
    except TelegramBadRequest as err:
        logger.error("Cannot send message due to bad request error")
        logger.exception(err)
        return
    except TelegramForbiddenError as err:
        logger.warning("Cannot send message due to forbidden error.")
        logger.exception(err)
        return
    except TelegramRetryAfter as err:
        logger.warning("Cannot send message due to flood error.")
        logger.exception(err)
        raise err
    except Exception as err:
        logger.exception(err)
        raise err

    logger.info("Message was sent.", tg_id=tg_id)
    logger.debug("Message content:\n%s", message)


@broker.task(retry_on_error=True, max_retries=3)
@inject
async def process_resume(
    user_id: str,
    resume_id: str,
    object_name: str,
    file_name: str,
    async_storage: AsyncStorage = Provide["s3_async_storage"],
    telegram_template: TelegramTemplate = Provide["telegram_template"],
    user_service: services.UserService = Provide["user_service"],
    resume_service: services.ResumeService = Provide["resume_service"],
    transaction_manager: AsyncTransactionManager = Provide["async_transaction_manager_scoped"],
    context: Context = _taskiq_context,
) -> None:
    log = logger.bind(
        user_id=user_id,
        resume_id=resume_id,
        object_name=object_name,
        file_name=file_name,
    )
    log.info("Starting resume processing.")

    user = await user_service.get_current_user(domains.UserID(user_id))
    if user is None:
        log.error("User not found.")
        return

    tg_id = int(user.messenger_id)
    log = log.bind(tg_id=tg_id)

    retries = int(context.message.labels.get("_retries", 0))
    max_retries = int(context.message.labels.get("max_retries", 3))

    async with transaction_manager:
        try:
            await resume_service.update_record_status(
                resume_id=domains.ResumeID(resume_id),
                status=domains.ResumeProcessingStatus.PROCESSING,
            )

            file_data = await async_storage.get_bytes(object_name)
            log.info("Resume file downloaded from storage.")

            extractor = TextExtractorFactory.get(file_name)
            resume_text = extractor.extract(file_data)
            log.info("Resume text extracted.", length=len(resume_text))

            chunks = await resume_service.save_metadata(
                resume_id=domains.ResumeID(resume_id),
                user_id=domains.UserID(user_id),
                first_name=user.first_name,
                last_name=user.last_name or "",
                resume_text=resume_text,
            )
            log.info("Resume saved to vector DB.", chunks_count=len(chunks))

            title = domains.extract_title_from_resume_text(resume_text)
            if title:
                await resume_service.update_record_title(resume_id=domains.ResumeID(resume_id), title=title)

            await resume_service.update_record_status(
                resume_id=domains.ResumeID(resume_id),
                status=domains.ResumeProcessingStatus.DONE,
            )

            text = telegram_template.render("resume/done.html", None)
            await send_tg_bot_message.kiq(tg_id, text)
        except Exception:
            log.exception("Resume processing failed.", attempt=retries + 1)

            try:
                await resume_service.update_record_status(
                    resume_id=domains.ResumeID(resume_id),
                    status=domains.ResumeProcessingStatus.FAILED,
                )
            except Exception:
                log.exception("Failed to update resume status to FAILED.")

            if retries + 1 >= max_retries:
                text = telegram_template.render("resume/failed.html", None)
                await send_tg_bot_message.kiq(tg_id, text)

            raise


@broker.task()
@inject
async def parse_job(
    user_id: str,
    resume_id: str,
    job_url: str,
    job_parser_agent: JobParserAgent = Provide["job_parser_agent"],
    tg_bot: Bot = Provide["tg_bot_client"],
    user_service: services.UserService = Provide["user_service"],
    job_service: services.JobService = Provide["job_service"],
    job_state_repo: repos.JobStateRepository = Provide["redis_job_state_repo"],
    transaction_manager: AsyncTransactionManager = Provide["async_transaction_manager_scoped"],
) -> None:
    log = logger.bind(
        user_id=user_id,
        resume_id=resume_id,
        job_url=job_url,
    )
    log.info("Starting vacancy parsing.")

    async with transaction_manager:
        user = await user_service.get_current_user(domains.UserID(user_id))
        if user is None:
            log.error("User not found.")
            return

        tg_id = int(user.messenger_id)
        log = log.bind(tg_id=tg_id)

        try:
            result = await job_parser_agent.run(job_reference=job_url)
        except Exception:
            log.error("Vacancy parsing failed.")
            await send_tg_bot_message.kiq(tg_id, "Failed to parse the vacancy. Please try again later.")
            return
        finally:
            await job_state_repo.clear_active(user_id=domains.UserID(user_id))

        if result.result is None:
            log.error("Vacancy parsing returned no result.")
            await send_tg_bot_message.kiq(tg_id, "Failed to parse the vacancy. Please try again later.")
            return

        metadata = result.result.model_dump(exclude={"text"})
        job_record = await job_service.create_record(
            user_id=domains.UserID(user_id),
            resume_id=domains.ResumeID(resume_id),
            title=result.result.job_title,
            url=job_url,
            metadata_=metadata,
        )
        log.info("Job record created.", job_id=str(job_record.id))

        chunks = await job_service.save_metadata(
            job_id=job_record.id,
            user_id=domains.UserID(user_id),
            resume_id=domains.ResumeID(resume_id),
            job_text=result.result.text,
        )
        log.info("Job metadata saved to vector DB.", chunks_count=len(chunks))

        data = result.model_dump_json(indent=2)
        document = BufferedInputFile(
            data.encode(),
            filename="vacancy.json",
        )
        await tg_bot.send_document(tg_id, document=document)
