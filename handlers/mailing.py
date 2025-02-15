from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_IDS
from database import get_all_users
import asyncio
import logging

router = Router()

class MailingStates(StatesGroup):
    WAITING_FOR_TEXT = State()
    WAITING_FOR_CONFIRMATION = State()
    WAITING_FOR_BUTTON = State()

@router.message(Command("mailing"))
async def start_mailing(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return  
    
    await message.answer("📢 Введите текст рассылки (или отправьте фото с подписью).")
    await state.set_state(MailingStates.WAITING_FOR_TEXT)

@router.message(StateFilter(MailingStates.WAITING_FOR_TEXT))
async def process_mailing_text_or_photo(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    if message.photo:
        mailing_text = message.caption or ""
        photo_id = message.photo[-1].file_id
    else:
        mailing_text = message.text or ""
        photo_id = None

    if not mailing_text.strip():
        await message.answer("❌ Текст обязателен! Введите текст ещё раз или прикрепите фото с подписью.")
        return
    
    await state.update_data(text=mailing_text, photo=photo_id)
    await message.answer("✅ Текст принят. Хотите добавить кнопку? (да/нет)")
    await state.set_state(MailingStates.WAITING_FOR_BUTTON)

@router.message(StateFilter(MailingStates.WAITING_FOR_BUTTON))
async def process_mailing_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    response = message.text.strip().lower()
    if response == "да":
        await message.answer("🔗 Введите текст и ссылку для кнопки в формате: `Текст кнопки | https://пример.ру`")
    elif response == "нет":
        await message.answer("✅ Кнопка пропущена. Запустить рассылку? (да/нет)")
        await state.set_state(MailingStates.WAITING_FOR_CONFIRMATION)
    else:
        if "|" in response:
            button_text, button_url = map(str.strip, response.split("|", 1))
            if not button_url.startswith("http"):
                await message.answer("❌ Неверная ссылка! Укажите полный URL (http/https).")
                return
            await state.update_data(button=(button_text, button_url))

        await message.answer("✅ Кнопка добавлена. Запустить рассылку? (да/нет)")
        await state.set_state(MailingStates.WAITING_FOR_CONFIRMATION)

@router.message(StateFilter(MailingStates.WAITING_FOR_CONFIRMATION))
async def confirm_mailing(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return
    
    if message.text.strip().lower() != "да":
        await message.answer("❌ Рассылка отменена.")
        await state.clear()
        return
    
    data = await state.get_data()
    mailing_text = data.get("text", "")
    photo_id = data.get("photo", None)
    button_data = data.get("button")

    markup = None
    if button_data:
        button_text, button_url = button_data
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=button_text, url=button_url)]]
        )

    await message.answer("📤 Начинаю рассылку...")
    users = get_all_users()
    success, failed = 0, 0

    for user in users:
        try:
            if photo_id:
                await message.bot.send_photo(chat_id=user, photo=photo_id, caption=mailing_text, reply_markup=markup)
            else:
                await message.bot.send_message(chat_id=user, text=mailing_text, reply_markup=markup)
            success += 1
        except Exception as e:
            failed += 1
            logging.warning(f"Ошибка отправки пользователю {user}: {e}")
        await asyncio.sleep(0.1)  

    await message.answer(f"✅ Рассылка завершена!\n✔️ Отправлено: {success}\n❌ Ошибок: {failed}")
    await state.clear()
