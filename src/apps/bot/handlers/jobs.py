import math
import uuid

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import dto
from core import services
from infra.bot.keyboards import get_paginated_list_keyboard
from infra.bot.template import TelegramTemplate
from utils.lang import _
from utils.pagination import PageSizePagination

from ..utils import get_lang
from ..utils import send_response

router = Router(name=__name__)

_JOBS_PAGE_PREFIX = "jobs_page_"
_JOBS_ITEM_PREFIX = "jobs_item_"
_JOBS_BACK_PREFIX = "jobs_back_"
_JOBS_DELETE_PREFIX = "jobs_del_"
_JOBS_PAGE_SIZE = 5


@router.message(Command("jobs"))
@inject
async def jobs(
    message: Message,
    user: dto.UserOutDTO,
    job_service: services.JobService = Provide["job_service"],
) -> None:
    await _show_jobs_list(
        message=message,
        user=user,
        page=1,
        job_service=job_service,
    )


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
@inject
async def jobs_item_select(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    job_service: services.JobService = Provide["job_service"],
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    item_id = (callback.data or "")[len(_JOBS_ITEM_PREFIX) :]
    await callback.answer()

    job = await job_service.get_by_pk(uuid.UUID(item_id))
    if not job:
        if isinstance(callback.message, Message):
            await callback.message.edit_text(_("Vacancy not found."))
        return

    lang = get_lang(callback.from_user)
    text = telegram_template.render(
        "job/detail.html",
        lang,
        title=job.title,
        url=job.url,
        date_str=job.created_at.strftime("%d.%m.%Y %H:%M"),
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_("🗑 Delete"),
                    callback_data=f"{_JOBS_DELETE_PREFIX}{item_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=_("⬅️ Back"),
                    callback_data=f"{_JOBS_BACK_PREFIX}1",
                ),
            ],
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith(_JOBS_BACK_PREFIX))
@inject
async def jobs_back(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    job_service: services.JobService = Provide["job_service"],
) -> None:
    page_str = (callback.data or "")[len(_JOBS_BACK_PREFIX) :]
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


@router.callback_query(F.data.startswith(_JOBS_DELETE_PREFIX))
@inject
async def jobs_delete(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    job_service: services.JobService = Provide["job_service"],
) -> None:
    item_id = (callback.data or "")[len(_JOBS_DELETE_PREFIX) :]
    await callback.answer()

    job = await job_service.get_by_pk(uuid.UUID(item_id))
    if not job:
        if isinstance(callback.message, Message):
            await callback.message.edit_text(_("Vacancy not found."))
        return

    await job_service.delete(job)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(_("Vacancy deleted."))


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
