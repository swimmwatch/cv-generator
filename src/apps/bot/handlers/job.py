from aiogram import F
from aiogram import Router
from aiogram.enums import ContentType
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
from utils.lang import _
from utils.net import is_url_reachable
from utils.net import is_valid_url

from ..filters import HasSufficientCreditsFilter
from ..filters import NoActiveJobParsingFilter
from ..states import JobStates
from ..tasks import parse_job
from ..utils import get_lang
from ..utils import send_response

router = Router(name=__name__)


@router.message(
    Command("job"),
    NoActiveJobParsingFilter(),
    HasSufficientCreditsFilter(domains.CreditAction.JOB_POSTING),
)
async def job(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await state.set_state(JobStates.waiting_for_url)
    await send_response(message, _("Please send a link to the job posting."))


@router.message(Command("job"), NoActiveJobParsingFilter())
@inject
async def job_insufficient_credits(
    message: Message,
    user: dto.UserOutDTO,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    lang = get_lang(message.from_user)
    text = telegram_template.render(
        "balance/insufficient.html",
        lang,
        cost=int(domains.CreditAction.JOB_POSTING),
        balance=user.balance,
    )
    await send_response(message, text)


@router.message(Command("job"))
async def job_already_processing(message: Message) -> None:
    await send_response(
        message,
        _("You already have a job parsing in progress. Please wait for it to finish."),
    )


@router.message(JobStates.waiting_for_url, Command("cancel"))
async def job_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_response(message, _("Job posting upload has been cancelled."))


@router.message(JobStates.waiting_for_url, F.content_type != ContentType.TEXT)
@router.message(JobStates.waiting_for_url, F.text, ~F.text.startswith("/"))
@inject
async def job_url_input(
    message: Message,
    user: dto.UserOutDTO,
    state: FSMContext,
    job_state_repo: repos.JobStateRepository = Provide["redis_job_state_repo"],
    user_service: services.UserService = Provide["user_service"],
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    url = (message.text or "").strip()

    if not is_valid_url(url):
        await send_response(message, _("Please send a valid link starting with http:// or https://"))
        return

    if not await is_url_reachable(url):
        await send_response(message, _("The link is not available. Please check the URL and try again."))
        return

    if not user.is_superuser:
        deducted = await user_service.deduct_credits(
            user_id=user.id,
            action=domains.CreditAction.JOB_POSTING,
        )
        if not deducted:
            lang = get_lang(message.from_user)
            text = telegram_template.render(
                "balance/insufficient.html",
                lang,
                cost=int(domains.CreditAction.JOB_POSTING),
                balance=user.balance,
            )
            await send_response(message, text)
            return

    await state.clear()
    await job_state_repo.set_active(user_id=user.id)

    await send_response(message, _("Parsing the vacancy. Please wait..."))
    await parse_job.kiq(user_id=str(user.id), job_url=url)
