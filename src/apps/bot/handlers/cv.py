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

from ..tasks import download_generated_cv
from ..utils import get_lang
from ..utils import send_response

router = Router(name=__name__)

_GENCV_PAGE_PREFIX = "gencv_page_"
_GENCV_ITEM_PREFIX = "gencv_item_"
_GENCV_BACK_PREFIX = "gencv_back_"
_GENCV_DOWNLOAD_PREFIX = "gencv_dl_"
_GENCV_PAGE_SIZE = 5


@router.message(Command("cv"))
@inject
async def cv(
    message: Message,
    user: dto.UserOutDTO,
    generated_cv_service: services.GeneratedCVService = Provide["generated_cv_service"],
) -> None:
    await _show_list(message=message, user=user, page=1, generated_cv_service=generated_cv_service)


@router.callback_query(F.data.startswith(_GENCV_PAGE_PREFIX))
@inject
async def cv_page(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    generated_cv_service: services.GeneratedCVService = Provide["generated_cv_service"],
) -> None:
    page_str = (callback.data or "")[len(_GENCV_PAGE_PREFIX) :]
    page = int(page_str) if page_str.isdigit() else 1
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show_list(
            message=callback.message,
            user=user,
            page=page,
            generated_cv_service=generated_cv_service,
            edit=True,
        )


@router.callback_query(F.data.startswith(_GENCV_ITEM_PREFIX))
@inject
async def cv_detail(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    generated_cv_service: services.GeneratedCVService = Provide["generated_cv_service"],
    job_service: services.JobService = Provide["job_service"],
    resume_service: services.ResumeService = Provide["resume_service"],
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    item_id = (callback.data or "")[len(_GENCV_ITEM_PREFIX) :]
    await callback.answer()

    generated_cv = await generated_cv_service.get_by_pk(uuid.UUID(item_id))
    if not generated_cv:
        if isinstance(callback.message, Message):
            await callback.message.edit_text(_("Generated CV not found."))
        return

    job = await job_service.get_by_pk(generated_cv.job_id)
    resume = await resume_service.get_by_pk(generated_cv.resume_id)
    lang = get_lang(callback.from_user)
    date_str = generated_cv.created_at.strftime("%d.%m.%Y %H:%M")

    text = telegram_template.render(
        "generated_cv/detail.html",
        lang,
        job=job,
        resume=resume,
        date_str=date_str,
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_("⬇️ Download"),
                    callback_data=f"{_GENCV_DOWNLOAD_PREFIX}{item_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=_("⬅️ Back"),
                    callback_data=f"{_GENCV_BACK_PREFIX}1",
                ),
            ],
        ]
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith(_GENCV_BACK_PREFIX))
@inject
async def cv_back(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    generated_cv_service: services.GeneratedCVService = Provide["generated_cv_service"],
) -> None:
    page_str = (callback.data or "")[len(_GENCV_BACK_PREFIX) :]
    page = int(page_str) if page_str.isdigit() else 1
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show_list(
            message=callback.message,
            user=user,
            page=page,
            generated_cv_service=generated_cv_service,
            edit=True,
        )


@router.callback_query(F.data.startswith(_GENCV_DOWNLOAD_PREFIX))
@inject
async def cv_download(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    generated_cv_service: services.GeneratedCVService = Provide["generated_cv_service"],
) -> None:
    item_id = (callback.data or "")[len(_GENCV_DOWNLOAD_PREFIX) :]
    await callback.answer()

    generated_cv = await generated_cv_service.get_by_pk(uuid.UUID(item_id))
    if not generated_cv:
        if isinstance(callback.message, Message):
            await callback.message.edit_text(_("Generated CV not found."))
        return

    if isinstance(callback.message, Message):
        await callback.message.edit_text(_("Sending the document..."))

    await download_generated_cv.kiq(
        int(user.messenger_id),
        generated_cv.object_name,
        generated_cv.file_name,
    )


async def _show_list(
    message: Message,
    user: dto.UserOutDTO,
    page: int,
    generated_cv_service: services.GeneratedCVService,
    edit: bool = False,
) -> None:
    items, total = await generated_cv_service.get_user_generated_cvs(
        user_id=user.id,
        pagination=PageSizePagination(page_size=_GENCV_PAGE_SIZE, page=page),
    )

    if not items and page == 1:
        text = _("You don't have any generated CVs yet. Use /generate to create one.")
        if edit:
            await message.edit_text(text)
        else:
            await send_response(message, text)
        return

    total_pages = max(1, math.ceil(total / _GENCV_PAGE_SIZE))
    offset = (page - 1) * _GENCV_PAGE_SIZE

    def item_title(item: dto.GeneratedCVOutDTO) -> str:
        n = offset + items.index(item) + 1
        date_str = item.created_at.strftime("%d.%m.%Y")
        display = item.file_name
        return f"#{n} \u2014 {display} ({date_str})"

    keyboard_rows = get_paginated_list_keyboard(
        current_page=page,
        total_pages=total_pages,
        items=items,
        item_title_getter=item_title,
        item_id_getter=lambda i: str(i.id),
        item_prefix_callback=_GENCV_ITEM_PREFIX,
        base_prefix=_GENCV_PAGE_PREFIX,
    )
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    text = _("Generated CVs (page %d of %d):") % (page, total_pages)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await send_response(message, text, keyboard=markup)
