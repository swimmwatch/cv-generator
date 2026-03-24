from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup


class GenerateStates(StatesGroup):
    selecting_resume = State()
    selecting_job = State()
