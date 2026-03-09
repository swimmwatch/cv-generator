from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from core import domains
from core import dto
from core import services
from infra.bot.template import TelegramTemplate
from utils.lang import _

from ..states import ResumeUploadStates
from ..tasks import process_resume
from ..utils import send_response

router = Router(name=__name__)


@router.message(Command("start"))
@inject
async def start(
    message: Message,
    state: FSMContext,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
) -> None:
    user = message.from_user
    lang = getattr(user, "language_code", None) if user else None

    response = telegram_template.render(
        "greet.html",
        lang,
        user=user,
    )
    await send_response(message, response)

    upload_prompt = telegram_template.render("resume/upload_prompt.html", lang)
    await send_response(message, upload_prompt)

    await state.set_state(ResumeUploadStates.waiting_for_file)


@router.message(ResumeUploadStates.waiting_for_file)
@inject
async def handle_resume_upload(
    message: Message,
    state: FSMContext,
    user: dto.UserOutDTO,
    telegram_template: TelegramTemplate = Provide["telegram_template"],
    resume_service: services.ResumeService = Provide["resume_service"],
) -> None:
    tg_user = message.from_user
    lang = getattr(tg_user, "language_code", None) if tg_user else None
    document = message.document

    if not document:
        text = _("Please upload a file in PDF or DOCX format.")
        text = telegram_template.render_error(text, lang)
        await send_response(message, text)
        return

    mime_type = document.mime_type or ""
    file_name = document.file_name or ""
    file_ext = ""
    if "." in file_name:
        file_ext = "." + file_name.rsplit(".", 1)[-1].lower()

    if mime_type not in domains.ALLOWED_RESUME_MIME_TYPES and file_ext not in domains.ALLOWED_RESUME_EXTENSIONS:
        formats = ", ".join(domains.ALLOWED_RESUME_EXTENSIONS)
        text = _("Invalid file format. Please upload your resume in one of the following formats: %s") % formats
        text = telegram_template.render_error(text, lang)
        await send_response(message, text)
        return

    bot = message.bot
    if bot is None:
        return
    file = await bot.download(document)
    if file is None:
        return
    file_data = file.read()

    object_name = await resume_service.upload(
        user_id=user.id,
        file_name=file_name,
        file_data=file_data,
        content_type=mime_type or "application/octet-stream",
    )

    resume_record = await resume_service.create_record(
        user_id=user.id,
        object_name=object_name,
        file_name=file_name,
    )

    await state.clear()

    processing_text = telegram_template.render("resume/processing.html", lang)
    await send_response(message, processing_text)

    await process_resume.kiq(
        user_id=str(user.id),
        resume_id=str(resume_record.id),
        object_name=object_name,
        file_name=file_name,
    )
