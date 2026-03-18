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

_CV_PAGE_PREFIX = "cv_page_"
_CV_RESUME_PREFIX = "cv_resume_"
_CV_PAGE_SIZE = 5


@router.message(Command("resumes"))
@inject
async def resumes(
    message: Message,
    user: dto.UserOutDTO,
    resume_service: services.ResumeService = Provide["resume_service"],
) -> None:
    await _show_cv_list(message=message, user=user, page=1, resume_service=resume_service)


@router.callback_query(F.data.startswith(_CV_PAGE_PREFIX))
@inject
async def cv_page(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    resume_service: services.ResumeService = Provide["resume_service"],
) -> None:
    page_str = (callback.data or "")[len(_CV_PAGE_PREFIX) :]
    page = int(page_str) if page_str.isdigit() else 1
    await callback.answer()
    if isinstance(callback.message, Message):
        await _show_cv_list(
            message=callback.message,
            user=user,
            page=page,
            resume_service=resume_service,
            edit=True,
        )


@router.callback_query(F.data.startswith(_CV_RESUME_PREFIX))
async def cv_resume_select(callback: CallbackQuery) -> None:
    await callback.answer()


async def _show_cv_list(
    message: Message,
    user: dto.UserOutDTO,
    page: int,
    resume_service: services.ResumeService,
    edit: bool = False,
) -> None:
    resumes, total = await resume_service.get_user_resumes(
        user_id=user.id,
        pagination=PageSizePagination(page_size=_CV_PAGE_SIZE, page=page),
    )

    if not resumes and page == 1:
        text = _("You haven't uploaded any resumes yet. Use /start to upload one.")
        if edit:
            await message.edit_text(text)
        else:
            await send_response(message, text)
        return

    total_pages = max(1, math.ceil(total / _CV_PAGE_SIZE))
    offset = (page - 1) * _CV_PAGE_SIZE

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
        item_prefix_callback=_CV_RESUME_PREFIX,
        base_prefix=_CV_PAGE_PREFIX,
    )
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    text = _("Your resumes (page %d of %d):") % (page, total_pages)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await send_response(message, text, keyboard=markup)
