import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from google import genai
from config import GEMINI_API_KEY
from database import get_consultation_credits, decrement_consultation_credits, add_consultation_credits
from handlers.payment import check_payment  # ✅ Импортируем функцию проверки платежа

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
router = Router()
conversation_context = {}
dialogue_start_times = {}

logging.basicConfig(level=logging.INFO)

@router.callback_query(F.data == "consultation")
async def consultation_menu(call: CallbackQuery):
    """Обрабатывает кнопку 'Консультация'. Проверяет доступные консультации, если их нет — предлагает оплату."""
    user_id = call.message.chat.id

    # Проверяем доступные консультации
    available_credits = get_consultation_credits(user_id) or 0  # Если None, то 0

    if available_credits == 0:
        # Если консультаций нет, предлагаем оплату
        payment_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💰 Оплатить 10 руб. (1 консультация)", callback_data="pay_consultation")],
                [InlineKeyboardButton(text="💰 Оплатить 40 руб. (4 консультации)", callback_data="pay_4_consultations")],
                [InlineKeyboardButton(text="✅ Я оплатил, проверить", callback_data="check_payment")]
            ]
        )
        await call.message.answer(
            "У вас нет доступных консультаций. Оплатите 10 руб. за 1 консультацию или 40 руб. за 4 консультации.",
            reply_markup=payment_keyboard
        )
        return

    # Если есть доступные консультации, начинаем диалог
    decrement_consultation_credits(user_id)  # ✅ Вычитаем 1 консультацию
    await call.message.answer("⌛ Ищу специалиста...")
    await asyncio.sleep(10)
    await call.message.answer("✅ Специалист найден! Напишите свой вопрос.")

    # Начинаем диалог
    conversation_context[user_id] = []
    dialogue_start_times[user_id] = datetime.now()

@router.callback_query(F.data == "check_payment")
async def check_payment_callback(call: CallbackQuery):
    """Проверяет статус оплаты и зачисляет консультации."""
    user_id = call.message.chat.id

    # Метки платежей
    label_1 = f"payment_{user_id}_1"
    label_4 = f"payment_{user_id}_4"

    logging.info(f"🔍 Запрос на проверку платежа от user_id={user_id}")

    if check_payment(label_4, 40.0):  # Если оплата за 4 консультации
        add_consultation_credits(user_id, 4)  # ✅ Добавляем 4 консультации
        await call.message.answer("✅ Оплата за 4 консультации подтверждена! Теперь у вас есть 4 консультации.")
    
    elif check_payment(label_1, 10.0):  # Если оплата за 1 консультацию (только если 40 руб. нет)
        add_consultation_credits(user_id, 1)  # ✅ Добавляем 1 консультацию
        await call.message.answer("✅ Оплата за 1 консультацию подтверждена! Теперь у вас есть 1 консультация.")
    
    else:
        await call.message.answer("❌ Оплата не найдена. Убедитесь, что платеж прошел.")

@router.message(lambda m: m.chat.id in conversation_context)
async def dialogue_message_handler(message: Message):
    """Обрабатывает диалог пользователя с ботом."""
    user_id = message.chat.id
    user_msg = message.text.strip() if message.text else ""

    if not user_msg:
        await message.answer("❌ Сообщение пусто. Введите текст.")
        return

    if user_id not in dialogue_start_times:
        await message.answer("Диалог неактивен. Начните новый диалог.")
        return

    if datetime.now() - dialogue_start_times[user_id] > timedelta(minutes=30):
        await message.answer("Диалог завершен по истечении 30 минут.")
        del conversation_context[user_id]
        del dialogue_start_times[user_id]
        return

    conversation_context[user_id].append({"role": "user", "content": user_msg})

    await message.answer("⌛ Получаю ответ...")
    await asyncio.sleep(2)

    try:
        dialogue_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_context[user_id]])
        full_prompt = f"Ты — профессиональный таролог. Вот история диалога:\n\n{dialogue_history}\n\nОтветь:"
        
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=full_prompt
        )
        answer = response.text.strip() if hasattr(response, 'text') and response.text else "Ответ не получен."

    except Exception as e:
        logging.error(f"Ошибка при запросе к Gemini: {e}")
        answer = "🚨 Ошибка. Попробуйте позже."

    conversation_context[user_id].append({"role": "assistant", "content": answer})

    # ✅ Добавлена кнопка "Завершить диалог"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Завершить диалог", callback_data="end_dialog")]]
    )

    await message.answer(f"🔮 Ответ специалиста:\n\n{answer}", reply_markup=keyboard)

@router.callback_query(F.data == "end_dialog")
async def end_dialog_handler(call: CallbackQuery):
    """Завершает диалог."""
    user_id = call.message.chat.id
    conversation_context.pop(user_id, None)
    dialogue_start_times.pop(user_id, None)
    await call.message.answer("Диалог завершен.")



