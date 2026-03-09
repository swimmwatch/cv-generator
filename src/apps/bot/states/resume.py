from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup


class ResumeUploadStates(StatesGroup):
    waiting_for_file = State()
