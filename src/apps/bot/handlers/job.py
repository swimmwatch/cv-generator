import math

import aiohttp
from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import domains
from core import dto
from core import repos
from core import services
from infra.bot.keyboards import get_paginated_list_keyboard
from utils.lang import _
from utils.net import is_valid_url
from utils.pagination import PageSizePagination

from ..filters import HasDoneResumeFilter
from ..filters import NoActiveJobParsingFilter
from ..states import JobStates
from ..tasks import parse_job
from ..utils import send_response

router = Router(name=__name__)

_JOB_PAGE_PREFIX = "job_page_"
_JOB_RESUME_PREFIX = "job_resume_"
_JOB_PAGE_SIZE = 5
_URL_CHECK_TIMEOUT = 10


@router.message(Command("job"), HasDoneResumeFilter(), NoActiveJobParsingFilter())
@inject
async def job(
    message: Message,
    user: dto.UserOutDTO,
    state: FSMContext,
    resume_service: services.ResumeService = Provide["resume_service"],
) -> None:
    await state.clear()
    await _show_resume_list(message=message, user=user, page=1, resume_service=resume_service)


@router.message(Command("job"), HasDoneResumeFilter())
async def job_already_processing(message: Message) -> None:
    await send_response(
        message,
        _("You already have a job parsing in progress. Please wait for it to finish."),
    )


@router.message(Command("job"))
async def job_no_resume(message: Message) -> None:
    await send_response(
        message,
        _("You don't have any processed resumes yet. Please upload a resume first using /start."),
    )


@router.callback_query(F.data.startswith(_JOB_PAGE_PREFIX))
@inject
async def job_page(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    resume_service: services.ResumeService = Provide["resume_service"],
) -> None:
    page_str = (callback.data or "")[len(_JOB_PAGE_PREFIX) :]
    page = int(page_str) if page_str.isdigit() else 1
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show_resume_list(
            message=callback.message,
            user=user,
            page=page,
            resume_service=resume_service,
            edit=True,
        )


@router.callback_query(F.data.startswith(_JOB_RESUME_PREFIX))
async def job_resume_select(callback: CallbackQuery, state: FSMContext) -> None:
    resume_id = (callback.data or "")[len(_JOB_RESUME_PREFIX) :]
    await callback.answer()
    await state.update_data(resume_id=resume_id)
    await state.set_state(JobStates.waiting_for_url)
    if isinstance(callback.message, Message):
        await callback.message.edit_text(_("Please send a link to the job posting."))


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

    data = await state.get_data()
    resume_id = data.get("resume_id")
    if not resume_id:
        await state.clear()
        await send_response(message, _("Something went wrong. Please try /job again."))
        return

    await state.clear()
    await job_state_repo.set_active(user_id=user.id)
    await send_response(message, _("Parsing the vacancy. Please wait..."))
    await parse_job.kiq(user_id=str(user.id), resume_id=resume_id, job_url=url)


async def _is_url_reachable(url: str) -> bool:
    try:
        timeout = aiohttp.ClientTimeout(total=_URL_CHECK_TIMEOUT)
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=timeout, allow_redirects=True) as resp:
                return resp.status < 500
    except Exception:
        return False


async def _show_resume_list(
    message: Message,
    user: dto.UserOutDTO,
    page: int,
    resume_service: services.ResumeService,
    edit: bool = False,
) -> None:
    resumes, total = await resume_service.get_user_resumes(
        user_id=user.id,
        pagination=PageSizePagination(page_size=_JOB_PAGE_SIZE, page=page),
        status=domains.ResumeProcessingStatus.DONE,
    )

    if not resumes and page == 1:
        text = _("You haven't uploaded any resumes yet. Use /start to upload one.")
        if edit:
            await message.edit_text(text)
        else:
            await send_response(message, text)
        return

    total_pages = max(1, math.ceil(total / _JOB_PAGE_SIZE))
    offset = (page - 1) * _JOB_PAGE_SIZE

    def item_title(resume: dto.ResumeOutDTO) -> str:
        n = offset + resumes.index(resume) + 1
        display = resume.title or resume.file_name
        date_str = resume.created_at.strftime("%d.%m.%Y")
        return f"#{n} \u2014 {display} ({date_str})"

    keyboard_rows = get_paginated_list_keyboard(
        current_page=page,
        total_pages=total_pages,
        items=resumes,
        item_title_getter=item_title,
        item_id_getter=lambda r: str(r.id),
        item_prefix_callback=_JOB_RESUME_PREFIX,
        base_prefix=_JOB_PAGE_PREFIX,
    )
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    text = _("Select a resume for job matching (page %d of %d):") % (page, total_pages)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await send_response(message, text, keyboard=markup)
