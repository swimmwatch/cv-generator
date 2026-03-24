import asyncio
import math
import re

from aiogram import F
from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

from core import domains
from core import dto
from core import repos
from core import services
from infra.agents.chat import ChatAgent
from infra.bot.keyboards import get_paginated_list_keyboard
from infra.bot.template import TelegramTemplate
from utils.lang import _
from utils.pagination import PageSizePagination

from ..filters import HasDoneResumeFilter
from ..filters import HasJobFilter
from ..filters import HasSufficientCreditsFilter
from ..filters import NoPendingChatMessageFilter
from ..states import ChatStates
from ..utils import get_lang
from ..utils import send_response

router = Router(name=__name__)

_CHAT_RESUME_PAGE_PREFIX = "chat_r_page_"
_CHAT_RESUME_SELECT_PREFIX = "chat_r_sel_"
_CHAT_JOB_PAGE_PREFIX = "chat_j_page_"
_CHAT_JOB_SELECT_PREFIX = "chat_j_sel_"
_STREAM_UPDATE_INTERVAL = 1.0
_TYPING_INTERVAL = 4.0
_MIN_TEXT_CHANGE = 20
_PAGE_SIZE = 5
_TG_SPLIT_THRESHOLD = 3800

_HTML_TAG_PATTERN = re.compile(r"<(/?)(b|i|code|pre|a|s|u|blockquote)(\s[^>]*)?>")


def _get_open_tags(text: str) -> list[tuple[str, str]]:
    stack: list[tuple[str, str]] = []
    for match in _HTML_TAG_PATTERN.finditer(text):
        is_closing = match.group(1) == "/"
        tag_name = match.group(2)
        if is_closing:
            for i in range(len(stack) - 1, -1, -1):
                if stack[i][0] == tag_name:
                    stack.pop(i)
                    break
        else:
            stack.append((tag_name, match.group(0)))
    return stack


def _close_open_tags(open_tags: list[tuple[str, str]]) -> str:
    return "".join(f"</{name}>" for name, _ in reversed(open_tags))


def _reopen_tags(open_tags: list[tuple[str, str]]) -> str:
    return "".join(full_tag for _, full_tag in open_tags)


@router.message(Command("chat"), HasDoneResumeFilter(), HasJobFilter())
@inject
async def chat_start(
    message: Message,
    user: dto.UserOutDTO,
    state: FSMContext,
    resume_service: services.ResumeService = Provide["resume_service"],
) -> None:
    await state.clear()
    await state.set_state(ChatStates.selecting_resume)
    await _show_resume_list(
        message=message,
        user=user,
        page=1,
        resume_service=resume_service,
    )


@router.message(Command("chat"), HasDoneResumeFilter())
async def chat_no_jobs(message: Message) -> None:
    await send_response(
        message,
        _("You don't have any saved vacancies yet. Use /job to add one before starting a chat."),
    )


@router.message(Command("chat"), HasJobFilter())
async def chat_no_resume(message: Message) -> None:
    await send_response(
        message,
        _("You don't have any processed resumes yet. Use /resume to upload a resume before starting a chat."),
    )


@router.message(Command("chat"))
async def chat_no_resume_no_jobs(message: Message) -> None:
    await send_response(
        message,
        _(
            "To start a chat, you need a resume and a job posting. "
            "Use /resume to upload a resume and /job to add a job posting."
        ),
    )


@router.callback_query(ChatStates.selecting_resume, F.data.startswith(_CHAT_RESUME_PAGE_PREFIX))
@inject
async def chat_resume_page(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    resume_service: services.ResumeService = Provide["resume_service"],
) -> None:
    page_str = (callback.data or "")[len(_CHAT_RESUME_PAGE_PREFIX) :]
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


@router.callback_query(ChatStates.selecting_resume, F.data.startswith(_CHAT_RESUME_SELECT_PREFIX))
@inject
async def chat_resume_select(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    state: FSMContext,
    job_service: services.JobService = Provide["job_service"],
) -> None:
    resume_id = (callback.data or "")[len(_CHAT_RESUME_SELECT_PREFIX) :]
    await callback.answer()
    await state.update_data(resume_id=resume_id)
    await state.set_state(ChatStates.selecting_job)
    if isinstance(callback.message, Message):
        await _show_job_list(
            message=callback.message,
            user=user,
            page=1,
            job_service=job_service,
            edit=True,
        )


@router.callback_query(ChatStates.selecting_job, F.data.startswith(_CHAT_JOB_PAGE_PREFIX))
@inject
async def chat_job_page(
    callback: CallbackQuery,
    user: dto.UserOutDTO,
    job_service: services.JobService = Provide["job_service"],
) -> None:
    page_str = (callback.data or "")[len(_CHAT_JOB_PAGE_PREFIX) :]
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


@router.callback_query(ChatStates.selecting_job, F.data.startswith(_CHAT_JOB_SELECT_PREFIX))
async def chat_job_select(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    job_id = (callback.data or "")[len(_CHAT_JOB_SELECT_PREFIX) :]
    await callback.answer()
    await state.update_data(job_id=job_id)
    await state.set_state(ChatStates.chatting)

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            _("You can now ask questions. Send /cancel to exit the chat."),
            parse_mode=ParseMode.HTML,
        )


@router.message(Command("cancel"), ChatStates.chatting)
async def chat_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await send_response(message, _("Chat ended."))


@router.message(
    ChatStates.chatting,
    NoPendingChatMessageFilter(),
    HasSufficientCreditsFilter(domains.CreditAction.CHAT_MESSAGE),
)
@inject
async def chat_message(
    message: Message,
    user: dto.UserOutDTO,
    state: FSMContext,
    chat_agent: ChatAgent = Provide["chat_agent"],
    chat_state_repo: repos.ChatStateRepository = Provide["redis_chat_state_repo"],
    user_service: services.UserService = Provide["user_service"],
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    if message.chat is None or message.bot is None:
        return

    query = (message.text or "").strip()
    if not query:
        await send_response(message, _("Please send a text message."))
        return

    bot = message.bot
    chat_id = message.chat.id
    await bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING,
    )

    data = await state.get_data()
    resume_id = data.get("resume_id", "")
    job_id = data.get("job_id", "")

    if not resume_id or not job_id:
        await state.clear()
        await send_response(message, _("Something went wrong. Please try /chat again."))
        return

    raw_history = data.get("message_history")
    message_history = ModelMessagesTypeAdapter.validate_python(raw_history) if raw_history else None

    if not user.is_superuser:
        deducted = await user_service.deduct_credits(
            user_id=user.id,
            action=domains.CreditAction.CHAT_MESSAGE,
        )
        if not deducted:
            lang = get_lang(message.from_user)
            text = telegram_template.render(
                "balance/insufficient.html",
                lang,
                cost=int(domains.CreditAction.CHAT_MESSAGE),
                balance=user.balance,
            )
            await send_response(message, text)
            return

    await chat_state_repo.set_active(user.id)

    reply = await bot.send_message(chat_id=chat_id, text="⏳")

    full_text = ""
    current_msg_text = ""
    last_sent_text = ""
    last_update_time = 0.0
    typing_active = True

    async def _keep_typing() -> None:
        while typing_active:
            try:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except TelegramBadRequest:
                pass
            await asyncio.sleep(_TYPING_INTERVAL)

    typing_task = asyncio.create_task(_keep_typing())

    async def _on_delta(delta: str) -> None:
        nonlocal full_text, current_msg_text, last_sent_text, last_update_time, typing_active, reply
        if typing_active:
            typing_active = False
        full_text += delta
        current_msg_text += delta

        if len(current_msg_text) > _TG_SPLIT_THRESHOLD:
            open_tags = _get_open_tags(current_msg_text)
            closing = _close_open_tags(open_tags)
            try:
                await reply.edit_text(
                    text=current_msg_text + closing,
                    parse_mode=ParseMode.HTML,
                )
            except TelegramBadRequest:
                pass
            reopening = _reopen_tags(open_tags)
            reply = await bot.send_message(chat_id=chat_id, text="⏳")
            current_msg_text = reopening
            last_sent_text = ""
            last_update_time = 0.0
            return

        now = asyncio.get_event_loop().time()
        text_diff = len(current_msg_text) - len(last_sent_text)

        if text_diff >= _MIN_TEXT_CHANGE and (now - last_update_time) >= _STREAM_UPDATE_INTERVAL:
            try:
                await reply.edit_text(
                    text=current_msg_text + " ▌",
                    parse_mode=ParseMode.HTML,
                )
                last_sent_text = current_msg_text
                last_update_time = now
            except TelegramBadRequest:
                pass

    try:
        full_text, messages = await chat_agent.stream(
            query=query,
            user_id=str(user.id),
            resume_id=resume_id,
            job_id=job_id,
            on_delta=_on_delta,
            message_history=message_history,
        )

        await state.update_data(message_history=to_jsonable_python(messages))

        if full_text:
            try:
                await reply.edit_text(
                    text=current_msg_text,
                    parse_mode=ParseMode.HTML,
                )
            except TelegramBadRequest:
                try:
                    await reply.edit_text(text=current_msg_text)
                except TelegramBadRequest:
                    pass

            await bot.send_message(
                chat_id=chat_id,
                text=_("To stop the chat, use /cancel"),
                parse_mode=ParseMode.HTML,
            )
        else:
            await reply.edit_text(
                text=_("No data found. Please upload documents first."),
                parse_mode=ParseMode.HTML,
            )
    except Exception:
        error_text = _("An error occurred while generating a response. Please try again.")
        text = current_msg_text or error_text
        try:
            await reply.edit_text(text=text)
        except TelegramBadRequest:
            await bot.send_message(chat_id=chat_id, text=text)
    finally:
        typing_active = False
        typing_task.cancel()
        await chat_state_repo.clear_active(user.id)


@router.message(ChatStates.chatting, NoPendingChatMessageFilter())
@inject
async def chat_insufficient_credits(
    message: Message,
    user: dto.UserOutDTO,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    lang = get_lang(message.from_user)
    text = telegram_template.render(
        "balance/insufficient.html",
        lang,
        cost=int(domains.CreditAction.CHAT_MESSAGE),
        balance=user.balance,
    )
    await send_response(message, text)


@router.message(ChatStates.chatting)
async def chat_message_pending(message: Message) -> None:
    await send_response(
        message,
        _("Please wait for the previous response to finish before sending a new message."),
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
        pagination=PageSizePagination(page_size=_PAGE_SIZE, page=page),
        status=domains.ResumeProcessingStatus.DONE,
    )

    if not resumes and page == 1:
        text = _("You haven't uploaded any resumes yet. Use /resume to upload one.")
        if edit:
            await message.edit_text(text)
        else:
            await send_response(message, text)
        return

    total_pages = max(1, math.ceil(total / _PAGE_SIZE))
    offset = (page - 1) * _PAGE_SIZE

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
        item_prefix_callback=_CHAT_RESUME_SELECT_PREFIX,
        base_prefix=_CHAT_RESUME_PAGE_PREFIX,
    )
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    text = _("Select a resume for chat (page %d of %d):") % (page, total_pages)

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
        pagination=PageSizePagination(page_size=_PAGE_SIZE, page=page),
    )

    if not job_list and page == 1:
        text = _("You don't have any saved vacancies yet. Use /job to parse one.")
        if edit:
            await message.edit_text(text)
        else:
            await send_response(message, text)
        return

    total_pages = max(1, math.ceil(total / _PAGE_SIZE))
    offset = (page - 1) * _PAGE_SIZE

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
        item_prefix_callback=_CHAT_JOB_SELECT_PREFIX,
        base_prefix=_CHAT_JOB_PAGE_PREFIX,
    )
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    text = _("Select a vacancy for chat (page %d of %d):") % (page, total_pages)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await send_response(message, text, keyboard=markup)
