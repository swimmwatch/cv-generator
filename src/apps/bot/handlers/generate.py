import math

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
from core import services
from infra.bot.keyboards import get_paginated_list_keyboard
from utils.lang import _
from utils.pagination import PageSizePagination

from ..filters import HasDoneResumeFilter
from ..states import GenerateStates
from ..tasks import generate_cv
from ..utils import send_response

router = Router(name=__name__)

_GEN_RESUME_PAGE_PREFIX = "gen_r_page_"
_GEN_RESUME_SELECT_PREFIX = "gen_r_sel_"
_GEN_JOB_PAGE_PREFIX = "gen_j_page_"
_GEN_JOB_SELECT_PREFIX = "gen_j_sel_"
_GEN_PAGE_SIZE = 5


@router.message(Command("generate"), HasDoneResumeFilter())
@inject
async def generate(
    message: Message,
    user: dto.UserOutDTO,
    state: FSMContext,
    resume_service: services.ResumeService = Provide["resume_service"],
) -> None:
    await state.clear()
    await _show_resume_list(message=message, user=user, page=1, resume_service=resume_service)


@router.message(Command("generate"))
async def generate_no_resume(message: Message) -> None:
    await send_response(
        message,
        _("You don't have any processed resumes yet. Please upload a resume first using /start."),
    )


@router.callback_query(F.data.startswith(_GEN_RESUME_PAGE_PREFIX))
@inject
async def generate_resume_page(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    resume_service: services.ResumeService = Provide["resume_service"],
) -> None:
    page_str = (callback.data or "")[len(_GEN_RESUME_PAGE_PREFIX) :]
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


@router.callback_query(F.data.startswith(_GEN_RESUME_SELECT_PREFIX))
@inject
async def generate_resume_select(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    state: FSMContext,
    job_service: services.JobService = Provide["job_service"],
) -> None:
    resume_id = (callback.data or "")[len(_GEN_RESUME_SELECT_PREFIX) :]
    await callback.answer()
    await state.update_data(resume_id=resume_id)
    await state.set_state(GenerateStates.selecting_job)
    if isinstance(callback.message, Message):
        await _show_job_list(
            message=callback.message,
            user=user,
            page=1,
            job_service=job_service,
            edit=True,
        )


@router.callback_query(GenerateStates.selecting_job, F.data.startswith(_GEN_JOB_PAGE_PREFIX))
@inject
async def generate_job_page(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    job_service: services.JobService = Provide["job_service"],
) -> None:
    page_str = (callback.data or "")[len(_GEN_JOB_PAGE_PREFIX) :]
    page = int(page_str) if page_str.isdigit() else 1
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show_job_list(
            message=callback.message,
            user=user,
            page=page,
            job_service=job_service,
            edit=True,
        )


@router.callback_query(GenerateStates.selecting_job, F.data.startswith(_GEN_JOB_SELECT_PREFIX))
async def generate_job_select(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    state: FSMContext,
) -> None:
    job_id = (callback.data or "")[len(_GEN_JOB_SELECT_PREFIX) :]
    await callback.answer()

    data = await state.get_data()
    resume_id = data.get("resume_id")
    if not resume_id:
        await state.clear()
        if isinstance(callback.message, Message):
            await send_response(callback.message, _("Something went wrong. Please try /generate again."))
        return

    await state.clear()

    if isinstance(callback.message, Message):
        await callback.message.edit_text(_("Generating CV. Please wait..."))

    await generate_cv.kiq(
        str(user.id),
        resume_id,
        job_id,
        "",
    )


async def _show_resume_list(
    message: Message,
    user: dto.UserOutDTO,
    page: int,
    resume_service: services.ResumeService,
    edit: bool = False,
) -> None:
    resumes, total = await resume_service.get_user_resumes(
        user_id=user.id,
        pagination=PageSizePagination(page_size=_GEN_PAGE_SIZE, page=page),
        status=domains.ResumeProcessingStatus.DONE,
    )

    if not resumes and page == 1:
        text = _("You haven't uploaded any resumes yet. Use /start to upload one.")
        if edit:
            await message.edit_text(text)
        else:
            await send_response(message, text)
        return

    total_pages = max(1, math.ceil(total / _GEN_PAGE_SIZE))
    offset = (page - 1) * _GEN_PAGE_SIZE

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
        item_prefix_callback=_GEN_RESUME_SELECT_PREFIX,
        base_prefix=_GEN_RESUME_PAGE_PREFIX,
    )
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    text = _("Select a resume for CV generation (page %d of %d):") % (page, total_pages)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await send_response(message, text, keyboard=markup)


async def _show_job_list(
    message: Message,
    user: dto.UserOutDTO,
    page: int,
    job_service: services.JobService,
    edit: bool = False,
) -> None:
    job_list, total = await job_service.get_user_jobs(
        user_id=user.id,
        pagination=PageSizePagination(page_size=_GEN_PAGE_SIZE, page=page),
    )

    if not job_list and page == 1:
        text = _("You don't have any saved vacancies yet. Use /job to parse one.")
        if edit:
            await message.edit_text(text)
        else:
            await send_response(message, text)
        return

    total_pages = max(1, math.ceil(total / _GEN_PAGE_SIZE))
    offset = (page - 1) * _GEN_PAGE_SIZE

    def item_title(job: dto.JobOutDTO) -> str:
        n = offset + job_list.index(job) + 1
        date_str = job.created_at.strftime("%d.%m.%Y")
        return f"#{n} \u2014 {job.title} ({date_str})"

    keyboard_rows = get_paginated_list_keyboard(
        current_page=page,
        total_pages=total_pages,
        items=job_list,
        item_title_getter=item_title,
        item_id_getter=lambda j: str(j.id),
        item_prefix_callback=_GEN_JOB_SELECT_PREFIX,
        base_prefix=_GEN_JOB_PAGE_PREFIX,
    )
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    text = _("Select a vacancy for CV generation (page %d of %d):") % (page, total_pages)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await send_response(message, text, keyboard=markup)
