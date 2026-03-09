import math

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import dto
from core import services
from infra.bot.keyboards import get_paginated_list_keyboard
from utils.lang import _
from utils.pagination import PageSizePagination

from ..utils import send_response

router = Router(name=__name__)

_JOBS_PAGE_PREFIX = "jobs_page_"
_JOBS_ITEM_PREFIX = "jobs_item_"
_JOBS_PAGE_SIZE = 5


@router.message(Command("jobs"))
@inject
async def jobs(
    message: Message,
    user: dto.UserOutDTO,
    job_service: services.JobService = Provide["job_service"],
) -> None:
    await _show_jobs_list(message=message, user=user, page=1, job_service=job_service)


@router.callback_query(F.data.startswith(_JOBS_PAGE_PREFIX))
@inject
async def jobs_page(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    job_service: services.JobService = Provide["job_service"],
) -> None:
    page_str = (callback.data or "")[len(_JOBS_PAGE_PREFIX) :]
    page = int(page_str) if page_str.isdigit() else 1
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show_jobs_list(
            message=callback.message,
            user=user,
            page=page,
            job_service=job_service,
            edit=True,
        )


@router.callback_query(F.data.startswith(_JOBS_ITEM_PREFIX))
async def jobs_item_select(callback: CallbackQuery) -> None:
    await callback.answer()


async def _show_jobs_list(
    message: Message,
    user: dto.UserOutDTO,
    page: int,
    job_service: services.JobService,
    edit: bool = False,
) -> None:
    job_list, total = await job_service.get_user_jobs(
        user_id=user.id,
        pagination=PageSizePagination(page_size=_JOBS_PAGE_SIZE, page=page),
    )

    if not job_list and page == 1:
        text = _("You don't have any saved vacancies yet. Use /job to parse one.")
        if edit:
            await message.edit_text(text)
        else:
            await send_response(message, text)
        return

    total_pages = max(1, math.ceil(total / _JOBS_PAGE_SIZE))
    offset = (page - 1) * _JOBS_PAGE_SIZE

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
        item_prefix_callback=_JOBS_ITEM_PREFIX,
        base_prefix=_JOBS_PAGE_PREFIX,
    )
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    text = _("Your vacancies (page %d of %d):") % (page, total_pages)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await send_response(message, text, keyboard=markup)
