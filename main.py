import asyncio
import os
from datetime import datetime
import smtplib
from email.message import EmailMessage
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from aiogram import Dispatcher, Bot, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from aiohttp.web_fileresponse import content_type

from messages import Answer
from dotenv import dotenv_values
from aiogram.fsm.storage.memory import MemoryStorage
from dbServing import UsersTable, db
from StateMachine import StateMachine
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode, ContentType

db.connect()
db.create_tables([UsersTable], safe=True)
config = dotenv_values(".env")
bot = Bot(token=config.get("bot_token"))
dp = Dispatcher(storage=MemoryStorage())


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

    if "last_bot_message_id" in dict_data.keys():
        await bot.delete_message(message.chat.id, dict_data["last_bot_message_id"])

    await state.update_data(TAKE_NAME=message.text)
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Подтвердить", callback_data="name_ok"))

    bot_message = await message.answer(
        f"Спасибо\\! Вы ввели\\:\n*{message.text}*\\.\nВсё верно\\? Если да\\, нажмите *Подтвердить*, если нет — отправьте ваше имя ещё раз\\.",
        reply_markup=builder.as_markup(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

    await state.update_data(last_bot_message_id=bot_message.message_id)

    dict_data = await state.get_data()
    print(dict_data)


@dp.callback_query()
async def callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "name_ok":
        await callback_query.message.delete()
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


@dp.message(StateFilter(StateMachine.BIRTHDAY))
async def get_date(message: types.Message, state: FSMContext):
    try:
        valid_date = datetime.strptime(message.text, '%d.%m.%Y')
    except ValueError:
        print(message.text)
        await message.answer(
            "Дата несоответсвует формату.\nПожалуйста, введите её в точности, как описано в шаблоне:\nДД.ММ.ГГГГ. ")
        return None

    await state.set_state(StateMachine.PAY_FOR_TICKET)
    await state.update_data(BIRTHDAY=valid_date)
    await message.answer(Answer.PAY_FOR_TICKET.value)
    print(await state.get_data())


def SendMail(ImgFileName, caption):
    with open(ImgFileName, 'rb') as f:
        img_data = f.read()

    msg = MIMEMultipart()
    msg['Subject'] = "Новый заказ"
    msg['From'] = config.get("mail_login")
    msg['To'] = "telnykhtimofei@yandex.ru"

    text = MIMEText(caption)
    msg.attach(text)
    image = MIMEImage(img_data, name=os.path.basename(ImgFileName))
    msg.attach(image)

    s = smtplib.SMTP(config.get("mail_server"), int(config.get("mail_port")))
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(config.get("mail_login"), config.get("mail_pass"))
    s.sendmail(config.get("mail_login"), "TelnykhTimofei@yandex.ru", msg.as_string())
    s.quit()


@dp.message(StateFilter(StateMachine.PAY_FOR_TICKET), F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    print(data["BIRTHDAY"], type(data["BIRTHDAY"]))
    UsersTable.create(tg_id=message.chat.id, full_name=data["TAKE_NAME"], birthday=data["BIRTHDAY"],
                      phone=data["PHONE_NUM"])
    caption = f'Новая покупка\nФИО: {data["TAKE_NAME"]}\nТелефон: {data["PHONE_NUM"]}\nДата рождения: {data["BIRTHDAY"].strftime("%d.%m.%Y")}'

    file_id = message.photo[-1].file_id
    file_info = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    await bot.send_photo(chat_id=message.chat.id, photo=file_id, caption=caption)

    current_directory = os.getcwd()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo_path = os.path.join(current_directory, f"photo_{timestamp}.jpg")

    # Сохраняем фото в текущий каталог
    with open(photo_path, "wb") as file:
        file.write(downloaded_file.read())

    # Чтение и прикрепление файла
    with open(photo_path, "rb"):
        file_name = os.path.basename(photo_path)
        try:
            SendMail(file_name, caption)
        except Exception:
            pass

    await message.answer(Answer.SEND_CONFIRMATION.value)

    os.remove(photo_path)


@dp.message(StateFilter(StateMachine.PAY_FOR_TICKET), F.document)
async def process_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    print(data["BIRTHDAY"], type(data["BIRTHDAY"]))
    UsersTable.create(tg_id=message.chat.id, full_name=data["TAKE_NAME"], birthday=data["BIRTHDAY"],
                      phone=data["PHONE_NUM"])
    caption = f'Новая покупка\nФИО: {data["TAKE_NAME"]}\nТелефон: {data["PHONE_NUM"]}\nДата рождения: {data["BIRTHDAY"].strftime("%d.%m.%Y")}'

    file_id = message.document.file_id
    file_info = await bot.get_file(file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    await bot.send_document(chat_id=message.chat.id, document=file_id, caption=caption)

    current_directory = os.getcwd()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    photo_path = os.path.join(current_directory, f"photo_{timestamp}.jpg")

    # Сохраняем фото в текущий каталог
    with open(photo_path, "wb") as file:
        file.write(downloaded_file.read())

    # Чтение и прикрепление файла
    with open(photo_path, "rb"):
        file_name = os.path.basename(photo_path)
        SendMail(file_name, caption)

    await message.answer(Answer.SEND_CONFIRMATION.value)

    os.remove(photo_path)

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
