import aiohttp
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import dto
from core import repos
from utils.lang import _
from utils.net import is_valid_url

from ..filters import NoActiveJobParsingFilter
from ..states import JobStates
from ..tasks import parse_job
from ..utils import send_response

router = Router(name=__name__)

_URL_CHECK_TIMEOUT = 10


@router.message(Command("job"), NoActiveJobParsingFilter())
async def job(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await state.set_state(JobStates.waiting_for_url)
    await send_response(message, _("Please send a link to the job posting."))


@router.message(Command("job"))
async def job_already_processing(message: Message) -> None:
    await send_response(
        message,
        _("You already have a job parsing in progress. Please wait for it to finish."),
    )


@router.message(JobStates.waiting_for_url)
@inject
async def job_url_input(
    message: Message,
    user: dto.UserOutDTO,
    state: FSMContext,
    job_state_repo: repos.JobStateRepository = Provide["redis_job_state_repo"],
) -> None:
    url = (message.text or "").strip()

    if not is_valid_url(url):
        await send_response(message, _("Please send a valid link starting with http:// or https://"))
        return

    if not await _is_url_reachable(url):
        await send_response(message, _("The link is not available. Please check the URL and try again."))
        return

    await state.clear()
    await job_state_repo.set_active(user_id=user.id)
    await send_response(message, _("Parsing the vacancy. Please wait..."))
    await parse_job.kiq(user_id=str(user.id), job_url=url)


async def _is_url_reachable(url: str) -> bool:
    try:
        timeout = aiohttp.ClientTimeout(total=_URL_CHECK_TIMEOUT)
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=timeout, allow_redirects=True) as resp:
                return resp.status < 500
    except Exception:
        return False
