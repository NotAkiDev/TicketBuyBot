from enum import Enum
from aiogram.fsm.state import StatesGroup, State


class StateMachine(StatesGroup):
    START = State()
    TAKE_NAME = State()
    BIRTHDAY = State()
    PHONE_NUM = State()
    PAY_FOR_TICKET = State()
