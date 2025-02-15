import logging
from aiogram import Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import YOOMONEY_WALLET, YOOMONEY_OAUTH_TOKEN
from yoomoney import Client

logging.basicConfig(level=logging.INFO)
yoomoney_client = Client(YOOMONEY_OAUTH_TOKEN)
router = Router()

def create_payment_link(amount: float, label: str):
    """Создает ссылку на оплату через YooMoney с меткой."""
    link = (
        f"https://yoomoney.ru/quickpay/confirm.xml?receiver={YOOMONEY_WALLET}"
        f"&quickpay-form=shop&sum={amount}&paymentType=AC&label={label}"
    )
    return link

def check_payment(label: str, amount: float, commission_rate: float = 0.05) -> bool:
    """Проверяет, была ли совершена оплата с учетом комиссии."""
    try:
        history = yoomoney_client.operation_history(records=30)
        logging.info(f"📌 Проверяем историю платежей. Найдено операций: {len(history.operations)}")

        # Допустимый диапазон суммы с учетом комиссии 5%
        min_amount = amount * (1 - commission_rate)  # Учитываем уменьшение суммы
        max_amount = amount * (1 + commission_rate)  # Если вдруг сумма больше

        for op in history.operations:
            logging.info(f"🔍 Проверяем операцию: label={op.label}, status={op.status}, amount={op.amount}")

            if op.label == label and op.status == "success" and min_amount <= float(op.amount) <= max_amount:
                logging.info(f"✅ Оплата найдена! label={label}, сумма={op.amount}")
                return True

        logging.warning(f"❌ Оплата не найдена: label={label}, ожидаемая сумма {min_amount:.2f} - {max_amount:.2f}")
        return False

    except Exception as e:
        logging.error(f"🚨 Ошибка при проверке оплаты: {e}")
        return False


@router.callback_query(lambda c: c.data == "pay_consultation")
async def pay_consultation(call: CallbackQuery):
    """Отправляет ссылку на оплату 1 консультации (10 руб.)"""
    user_id = call.message.chat.id
    label = f"payment_{user_id}_1"
    payment_link = create_payment_link(10.0, label)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Оплатить 10 руб.", url=payment_link)],
            [InlineKeyboardButton(text="✅ Я оплатил, проверить", callback_data="check_payment")]
        ]
    )
    await call.message.answer("Оплатите 10 рублей и нажмите кнопку 'Я оплатил, проверить'.", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "pay_4_consultations")
async def pay_4_consultations(call: CallbackQuery):
    """Отправляет ссылку на оплату 4 консультаций (40 руб.)"""
    user_id = call.message.chat.id
    label = f"payment_{user_id}_4"
    payment_link = create_payment_link(40.0, label)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Оплатить 40 руб. (4 консультации)", url=payment_link)],
            [InlineKeyboardButton(text="✅ Я оплатил, проверить", callback_data="check_payment")]
        ]
    )
    await call.message.answer("Оплатите 40 рублей и нажмите кнопку 'Я оплатил, проверить'.", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "check_payment")
async def check_payment_status(call: CallbackQuery):
    """Проверяет статус платежа и добавляет консультации."""
    user_id = call.message.chat.id
    label_1 = f"payment_{user_id}_1"
    label_4 = f"payment_{user_id}_4"

    from database import add_consultation_credits

    logging.info(f"🔍 Запрос на проверку платежа от user_id={user_id}")

    if check_payment(label_4, 40.0):  # Сначала проверяем оплату за 4 консультации
        add_consultation_credits(user_id, 4)
        await call.message.answer("✅ Оплата за 4 консультации подтверждена! Теперь у вас есть 4 консультации.")
    elif check_payment(label_1, 10.0):  # Затем проверяем оплату за 1 консультацию
        add_consultation_credits(user_id, 1)
        await call.message.answer("✅ Оплата за 1 консультацию подтверждена! Теперь вы можете задать вопрос.")
    else:
        await call.message.answer("❌ Оплата не найдена. Убедитесь, что платеж прошел.")

