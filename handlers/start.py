from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import TAROT_APP_URL, NATAL_APP_URL
from database import add_user

router = Router()

@router.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    add_user(user_id, username, first_name, last_name)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔮 Сделать расклад Таро", web_app=WebAppInfo(url=TAROT_APP_URL))],
            [InlineKeyboardButton(text="🌌 Получить натальную карту", web_app=WebAppInfo(url=NATAL_APP_URL))],
            [InlineKeyboardButton(text="✨ Гороскоп", callback_data="horoscope")],
            [InlineKeyboardButton(text="✨ Консультация Таролога", callback_data="consultation")]
        ]
    )
    await message.answer("Привет! Выберите, что вы хотите сделать:", reply_markup=keyboard)