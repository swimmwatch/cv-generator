from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup


class GenerateStates(StatesGroup):
    selecting_job = State()
