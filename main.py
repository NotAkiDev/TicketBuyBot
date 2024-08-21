import asyncio
from aiogram import Dispatcher, Bot, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from messages import Answer
from dotenv import dotenv_values
from aiogram.fsm.storage.memory import MemoryStorage
from dbServing import UsersTable, db
from StateMachine import StateMachine
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

db.connect()
db.create_tables([UsersTable], safe=True)
config = dotenv_values(".env")
bot = Bot(token=config.get("bot_token"))
dp = Dispatcher()


@dp.message(Command("start"))
async def start_handler(message: types.Message):
    kb = [[types.KeyboardButton(text="Купить билет 🎟")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, input_field_placeholder="Купить билет")

    await message.answer(Answer.START.value, reply_markup=keyboard)


@dp.message(F.text == "Купить билет 🎟")
async def start_process_buy(message: types.Message, state: FSMContext):
    await state.set_state(StateMachine.TAKE_NAME)
    await message.answer(Answer.TAKE_NAME.value, reply_markup=ReplyKeyboardRemove())


@dp.message(StateFilter(StateMachine.TAKE_NAME))
async def get_name(message: types.Message, state: FSMContext):
    dict_data = await state.get_data()
    if "TAKE_NAME" in dict_data.keys():
        await bot.delete_message(message.chat.id, message.message_id - 1)
    await state.update_data(TAKE_NAME=message.text)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Подтвердить", callback_data="name_ok"))
    await message.answer(
        f"Спасибо\\! Вы ввели\\:\n*{message.text}*\\.\nВсё верно\\? Если да\\, нажмите *Подтвердить*, если нет — отправьте ваше имя ещё раз\\.",
        reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN_V2)


@dp.callback_query()
async def callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "name_ok":
        await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        kb = [[types.KeyboardButton(text="📱 Отправить", request_contact=True)]]
        keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True,
                                             input_field_placeholder="Отправить номер телефона")
        await callback_query.message.answer(Answer.PHONE_REQUEST.value, reply_markup=keyboard)
        await state.set_state(StateMachine.PHONE_NUM)


@dp.message(StateFilter(StateMachine.PHONE_NUM))
async def get_contact(message: types.Message, state: FSMContext):
    contact = message.contact.phone_number
    await state.update_data(PHONE_NUM=contact)
    await message.answer(f"Принято\n{Answer.TAKE_BIRTHDATE.value}", reply_markup=ReplyKeyboardRemove())
    await state.set_state(StateMachine.BIRTHDAY)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
