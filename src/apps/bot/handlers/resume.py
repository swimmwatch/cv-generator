import io

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import domains
from core import dto
from core import repos
from core import services
from infra.bot.template import TelegramTemplate
from utils.extractors import EXTRACTORS
from utils.lang import _

from ..filters import HasSufficientCreditsFilter
from ..filters import NoActiveResumeProcessingFilter
from ..states import ResumeUploadStates
from ..tasks import process_resume
from ..utils import get_lang
from ..utils import send_response

router = Router(name=__name__)

_ALLOWED_EXTENSIONS = set(EXTRACTORS.keys())


@router.message(
    Command("resume"),
    NoActiveResumeProcessingFilter(),
    HasSufficientCreditsFilter(domains.CreditAction.RESUME_UPLOAD),
)
@inject
async def resume(
    message: Message,
    state: FSMContext,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    await state.clear()
    await state.set_state(ResumeUploadStates.waiting_for_file)
    lang = get_lang(message.from_user)
    text = telegram_template.render("resume/upload_prompt.html", lang)
    await send_response(message, text)


@router.message(Command("resume"), NoActiveResumeProcessingFilter())
@inject
async def resume_insufficient_credits(
    message: Message,
    user: dto.UserOutDTO,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    lang = get_lang(message.from_user)
    text = telegram_template.render(
        "balance/insufficient.html",
        lang,
        cost=int(domains.CreditAction.RESUME_UPLOAD),
        balance=user.balance,
    )
    await send_response(message, text)


@router.message(Command("resume"))
async def resume_already_processing(message: Message) -> None:
    await send_response(
        message,
        _("You already have a resume being processed. Please wait for it to finish."),
    )


@router.message(ResumeUploadStates.waiting_for_file)
@inject
async def resume_file_input(
    message: Message,
    user: dto.UserOutDTO,
    state: FSMContext,
    resume_service: services.ResumeService = Provide["resume_service"],
    user_service: services.UserService = Provide["user_service"],
    resume_state_repo: repos.ResumeStateRepository = Provide["redis_resume_state_repo"],
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    if not message.document:
        lang = get_lang(message.from_user)
        text = telegram_template.render("resume/upload_prompt.html", lang)
        await send_response(message, text)
        return

    file_name = message.document.file_name or "resume"
    ext = ("." + file_name.rsplit(".", 1)[-1].lower()) if "." in file_name else ""

    if ext not in _ALLOWED_EXTENSIONS:
        lang = get_lang(message.from_user)
        text = telegram_template.render("resume/upload_prompt.html", lang)
        await send_response(message, text)
        return

    if not message.bot:
        return

    file = await message.bot.download(message.document)
    if not file or not isinstance(file, io.BytesIO):
        await send_response(message, _("Failed to download the file. Please try again."))
        return

    file_data = file.read()
    content_type = message.document.mime_type or "application/octet-stream"

    object_name = await resume_service.upload(
        user_id=user.id,
        file_name=file_name,
        file_data=file_data,
        content_type=content_type,
    )

    resume_record = await resume_service.create_record(
        user_id=user.id,
        object_name=object_name,
        file_name=file_name,
    )

    await state.clear()

    if not user.is_superuser:
        deducted = await user_service.deduct_credits(
            user_id=user.id,
            action=domains.CreditAction.RESUME_UPLOAD,
        )
        if not deducted:
            lang = get_lang(message.from_user)
            text = telegram_template.render(
                "balance/insufficient.html",
                lang,
                cost=int(domains.CreditAction.RESUME_UPLOAD),
                balance=user.balance,
            )
            await send_response(message, text)
            return

    await resume_state_repo.set_active(user.id)

    lang = get_lang(message.from_user)
    text = telegram_template.render("resume/processing.html", lang)
    await send_response(message, text)

    await process_resume.kiq(
        user_id=str(user.id),
        resume_id=str(resume_record.id),
        object_name=object_name,
        file_name=file_name,
    )
