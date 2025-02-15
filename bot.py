import asyncio
import logging
import sqlite3
import time
from datetime import datetime

from translatepy import Translator
from google import genai

from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton, 
                           WebAppInfo, CallbackQuery, Message)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from yoomoney import Client
import psycopg2
import io
from aiogram.types import BufferedInputFile
from aiogram.filters import Command

# Если нужно использовать Google Gemini:
# from google import genai
# gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ================== Константы / настройки ==================

API_TOKEN = '8136585514:AAH2Pu0bWiNqBklVWPOiF2RaJBHxzMtLjfk'
TAROT_APP_URL = 'https://d6c1-169-150-209-163.ngrok-free.app/tarot/'
NATAL_APP_URL = 'https://d6c1-169-150-209-163.ngrok-free.app/natal/'
flask_url = "https://d6c1-169-150-209-163.ngrok-free.app/horoscope/today"
GEMINI_API_KEY = "AIzaSyCqE4taBEs1GJUh_pJQUqdGgcSEfGL8Pbc"

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

DB_NAME = "users.db"

logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Инициализация диспетчера и роутера
# dp = Dispatcher()
# dp = Dispatcher(storage=MemoryStorage())  # Включаем поддержку FSM
router = Router()

translator = Translator()

# ================== База данных ==================

POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "BecomeMillioners48"
POSTGRES_DB = "postgres"
POSTGRES_HOST = "localhost"  # или IP вашего сервера
POSTGRES_PORT = "5432"

def get_connection():
    """
    Создаёт и возвращает соединение с PostgreSQL.
    Не забывайте закрывать его после использования.
    """
    return psycopg2.connect(
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT
    )


# ================== База данных ==================
def init_db():
    """
    Инициализация базы данных PostgreSQL (синхронно, вызывается один раз при старте).
    Создает таблицу users, если её нет.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            free_consultation_used BOOLEAN NOT NULL DEFAULT FALSE,
            balance NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def add_user(user_id, username, first_name, last_name):
    """
    Добавление пользователя в БД (синхронно). 
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (%s, %s, %s, %s)
        """, (user_id, username, first_name, last_name))
        conn.commit()
    except Exception as e:
        # Можно отлавливать конкретное исключение уникальности:
        # if isinstance(e, UniqueViolation):
        #     pass
        logging.warning(f"Ошибка при добавлении пользователя {user_id}: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def get_user_count():
    """
    Возвращает количество пользователей в таблице users.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else 0

def has_used_free_consultation(user_id: int) -> bool:
    """
    Возвращает True, если пользователь уже использовал бесплатную консультацию.
    Если пользователя нет в таблице, по умолчанию считаем, что не использовал.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT free_consultation_used
        FROM users
        WHERE user_id = %s
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row is None:
        # Пользователя нет, значит он ещё не зарегистрирован
        return False
    return row[0]  # Это значение BOOLEAN

def set_free_consultation_used(user_id: int, used: bool):
    """
    Устанавливает флаг free_consultation_used для данного user_id.
    Если пользователя нет в базе, можно сначала add_user(...) или проигнорировать.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET free_consultation_used = %s
        WHERE user_id = %s
        """,
        (used, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

def get_balance(user_id: int) -> float:
    """
    Возвращает текущий баланс пользователя в рублях.
    Если пользователя нет, возвращает 0.0
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT balance
        FROM users
        WHERE user_id = %s
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row is None:
        return 0.0
    return float(row[0])

def add_to_balance(user_id: int, amount: float):
    """
    Прибавляет заданную сумму к балансу пользователя.
    Если такого пользователя нет, вы можете сначала вызывать add_user(...) или проигнорировать ошибку.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE users
        SET balance = balance + %s
        WHERE user_id = %s
        """,
        (amount, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_all_users():
    """
    Возвращает список всех user_id из таблицы users.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row[0] for row in rows]

# ================== Админка ==================
ADMIN_IDS = [2089704895]

def get_all_users_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, first_name, last_name, date_added FROM users")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


@router.message(Command("list_users"))
async def list_users(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return  # Игнорируем, если не админ

    rows = get_all_users_data()  # [(user_id, username, first_name, last_name, date_added), ...]

    if not rows:
        await message.answer("Пока что никто не зарегистрирован.")
        return

    # 1. Создаём байтовый буфер в оперативной памяти
    buffer = io.BytesIO()

    # 2. Заполняем его строками (в байтах)
    for row in rows:
        user_id_db = row[0]  # Предполагаем, что это user_id
        line = f"{user_id_db}\n"
        buffer.write(line.encode("utf-8"))

    # 3. Возвращаем «указатель» в начало буфера
    buffer.seek(0)

    # 4. Преобразуем содержимое буфера в bytes,
    #    т.к. BufferedInputFile ждёт просто «сырые» байты.
    file_bytes = buffer.getvalue()

    # 5. Создаём объект BufferedInputFile
    #    filename="user_ids.txt" — это имя, которое будет видно при загрузке
    file_to_send = BufferedInputFile(
        file=file_bytes,
        filename="user_ids.txt"
    )

    # 6. Отправляем документ
    await message.answer_document(document=file_to_send)

@router.message(Command("stats"))
async def stats_command(message: Message):
    """Показывает количество пользователей в БД (доступно только админам)."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом
    if user_id not in ADMIN_IDS:
        return  # Игнорируем запрос

    # Если админ, выводим количество пользователей
    count = get_user_count()
    await message.answer(f"Количество пользователей в боте: {count}")


class MailingStates(StatesGroup):
    WAITING_FOR_TEXT = State()
    WAITING_FOR_CONFIRMATION = State()
    WAITING_FOR_BUTTON = State()


@router.message(Command("mailing"))
async def start_mailing(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return  # Если не админ, игнорируем
    
    await message.answer("📢 Введите текст рассылки (или отправьте фото с подписью).")
    await state.set_state(MailingStates.WAITING_FOR_TEXT)


# ------------------------------
# Хендлер, который ловит текст/фото при состоянии WAITING_FOR_TEXT
# ------------------------------
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

# Хендлер для кнопки или пропуска
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
        # Предполагаем, что здесь пользователь сразу прислал "Текст кнопки | Ссылка"
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

    # Рассылаем всем
    users = get_all_users()
    success, failed = 0, 0

    for user in users:
        try:
            if photo_id:
                await bot.send_photo(chat_id=user, photo=photo_id, caption=mailing_text, reply_markup=markup)
            else:
                await bot.send_message(chat_id=user, text=mailing_text, reply_markup=markup)
            success += 1
        except Exception as e:
            failed += 1
            logging.warning(f"Ошибка отправки пользователю {user}: {e}")
        await asyncio.sleep(0.1)  # Небольшая пауза между отправками

    await message.answer(f"✅ Рассылка завершена!\n✔️ Отправлено: {success}\n❌ Ошибок: {failed}")
    await state.clear()


'''Конец админки'''

# Инициализируем БД при старте
init_db()

# ================== Хендлер /start ==================

@router.message(Command("start"))
async def start_command(message: Message):
    """Главное меню"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Добавляем пользователя в БД
    add_user(user_id, username, first_name, last_name)

    # Создаем inline-клавиатуру списком списков кнопок
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔮 Сделать расклад Таро",
                    web_app=WebAppInfo(url=TAROT_APP_URL)
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌌 Получить натальную карту",
                    web_app=WebAppInfo(url=NATAL_APP_URL)
                )
            ],
            [
                InlineKeyboardButton(
                    text="✨ Гороскоп",
                    callback_data="horoscope"
                )
            ],
            [
                InlineKeyboardButton(
                    text="✨ Консультация Таролога",
                    callback_data="consultation"
                )
            ]
        ]
    )

    await message.answer("Привет! Выберите, что вы хотите сделать:", reply_markup=keyboard)

# ================== Гороскоп ==================

zodiac_translation = {
    "Овен": "Aries", "Телец": "Taurus", "Близнецы": "Gemini", "Рак": "Cancer",
    "Лев": "Leo", "Дева": "Virgo", "Весы": "Libra", "Скорпион": "Scorpio",
    "Стрелец": "Sagittarius", "Козерог": "Capricorn", "Водолей": "Aquarius", "Рыбы": "Pisces"
}

@router.callback_query(F.data == "horoscope")
async def horoscope_menu(call: CallbackQuery):
    """Меню выбора типа гороскопа"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌞 Дневной гороскоп",
                    callback_data="daily_horoscope"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❤️ Любовный гороскоп",
                    callback_data="love_horoscope"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💼 Карьерный гороскоп",
                    callback_data="career_horoscope"
                )
            ]
        ]
    )

    await call.message.edit_text(
        text="Какой гороскоп хотите?",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data in ["daily_horoscope", "love_horoscope", "career_horoscope"])
async def select_zodiac(call: CallbackQuery):
    """Меню выбора знака зодиака"""
    horoscope_type_full = call.data  # daily_horoscope / love_horoscope / career_horoscope
    
    zodiac_signs = list(zodiac_translation.keys())
    # Формируем кнопки для каждого знака
    rows = []
    for sign in zodiac_signs:
        button = InlineKeyboardButton(
            text=sign,
            callback_data=f"{horoscope_type_full}_{sign}"
        )
        rows.append([button])  # Каждая кнопка в отдельной строке
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

    horoscope_texts_ru = {
        "daily_horoscope": "дневной гороскоп",
        "love_horoscope": "любовный гороскоп",
        "career_horoscope": "карьерный гороскоп"
    }
    display_text = horoscope_texts_ru.get(horoscope_type_full, "гороскоп")

    await call.message.edit_text(
        text=f"Вы выбрали {display_text}. Теперь выберите ваш знак зодиака:",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data.startswith("daily_") or c.data.startswith("love_") or c.data.startswith("career_"))
async def handle_zodiac_choice(call: CallbackQuery):
    """Обработка выбора знака зодиака и запроса к (условному) Gemini API"""
    user_id = call.message.chat.id
    type_full, zodiac_sign = call.data.rsplit('_', 1)   # например, "daily_horoscope", "Овен"
    horoscope_type = type_full.split('_')[0]           # daily / love / career

    # Словарь для отображения типа гороскопа на русском
    horoscope_texts_ru = {
        'daily': 'дневной гороскоп',
        'love': 'любовный гороскоп',
        'career': 'карьерный гороскоп'
    }

    # ❌ Убираем клавиатуру (скрываем кнопки)
    await call.message.edit_reply_markup(reply_markup=None)

    if horoscope_type not in horoscope_texts_ru:
        await bot.send_message(user_id, "❌ Ошибка: неверный тип гороскопа.")
        return

    today_date = datetime.now().strftime("%Y-%m-%d")

    # Уникальные промпты для каждого типа гороскопа
    horoscope_prompts = {
        'daily': f"""
Дай мне подробный дневной гороскоп для знака {zodiac_sign} на {today_date}. Не пиши про любовь и работу. Ответ оформи следующим образом:

Пример:
Ваш гороскоп на сегодня:

Сегодня звезды советуют {zodiac_sign} прислушаться к своей интуиции. Возможны неожиданные изменения, которые могут повлиять на ваше настроение и планы. День благоприятен для новых начинаний, но избегайте поспешных решений.

Сделай ответ четким, логичным и не длиннее 1000 символов.
""",
        'love': f"""
Дай мне подробный любовный гороскоп для знака {zodiac_sign} на {today_date}. Сосредоточься на чувствах, романтических отношениях, личной жизни и возможностях для новых знакомств. Ответ оформи следующим образом:

Пример:
Ваш любовный гороскоп на сегодня:

Сегодня {zodiac_sign} может почувствовать особую эмоциональную связь с близким человеком. Если у вас уже есть отношения, этот день идеален для теплого общения и искренних признаний. Одинокие представители знака могут встретить человека, который изменит их взгляды на любовь. Открывайте свое сердце.

Сделай ответ четким, логичным и не длиннее 1000 символов.
""",
        'career': f"""
Дай мне подробный карьерный гороскоп для знака {zodiac_sign} на {today_date}. Сосредоточься на вопросах работы, бизнеса, финансов и профессионального роста. Ответ оформи следующим образом:

Пример:
Ваш карьерный гороскоп на сегодня:

Сегодня {zodiac_sign} может ожидать новых перспективных предложений в карьере. Важно проявить инициативу и уверенность в себе. Возможно, вам придется решать сложные задачи, но правильный подход поможет вам достичь успеха. В финансовых вопросах лучше избегать необдуманных решений и крупных трат.

Сделай ответ четким, логичным и не длиннее 1000 символов.
"""
    }

    query_ru = horoscope_prompts[horoscope_type]
    logging.info(f"📨 Отправка запроса (гороскоп) к Gemini: {query_ru}")

    try:
        # ✅ Отправляем запрос в Gemini напрямую
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=query_ru
        )

        # Проверяем, что ответ не пустой
        if hasattr(response, 'text') and response.text:
            horoscope_russian = response.text.strip()
            logging.info(f"✅ Ответ от Gemini: {horoscope_russian}")
        else:
            logging.error("❌ Gemini вернул пустой ответ")
            horoscope_russian = "Я не смог сгенерировать гороскоп сейчас. Попробуйте позже."

        # ✅ Отправляем ответ в Telegram
        await bot.send_message(user_id, f"🔮 {horoscope_russian}")

    except Exception as e:
        logging.exception(f"🚨 Ошибка при запросе гороскопа: {str(e)}")
        await bot.send_message(user_id, "🚨 Ошибка при запросе гороскопа. Попробуйте позже.")

# ================== Консультация Таролога ==================

user_queries = {}         # { user_id: str|None } для первоначального запроса консультации
conversation_context = {} # { user_id: [ {role: "user"/"assistant", content: str}, ... ] }
free_consultation_used = set()  # пользователи, которые уже воспользовались бесплатной консультацией

# Твой токен YooMoney
# *** НАСТРОЙКА ЮMONEY ***

# 1) Номер вашего кошелька (обязательно). Формат обычно 4100XXXXXXXXXXXX.
YOOMONEY_WALLET = "4100117426905137"

# 2) OAuth-токен, полученный через yoomoney.Authorize(...), с нужными правами:
#    ["account-info", "operation-history", "operation-details", "payment-p2p", "payment-shop"]
YOOMONEY_OAUTH_TOKEN = "4100117426905137.EC1D8A38937E3F0CD1D7CBE9CCAF94E3507AA66D2BB0CF7E32282679BF7CF6E824ACF8FAEE30E31B2FFBF45742D12AAF2884133FAF32F3F854C2431A1B555E92AA3512C4C1FF105964B8A5599BA7942FAFBCD49A059DDF9743B534284B9931AE2B61DA3F02EA4F499B16065EA42CDB444799E016A14C9A247A5D761E27BAA560"

# Создаём клиента для запросов к API ЮMoney (проверка поступлений).
yoomoney_client = Client(YOOMONEY_OAUTH_TOKEN)

# Словарь для хранения данных об ожидании оплаты:
# { user_id: { "label": str, "amount": float, ... } }
pending_payments = {}

def create_yoomoney_quickpay_link(amount: float, user_id: int) -> tuple[str, str]:
    """
    Генерирует ссылку Quick Pay для перевода 'amount' рублей на YOOMONEY_WALLET.
    Возвращает (link, label).
      label - уникальная метка, чтобы потом проверить оплату в history.
    """
    label = f"tarot_{user_id}_pay"
    targets = f"Tarot Consultation user {user_id}"

    base_url = "https://yoomoney.ru/quickpay/confirm.xml"
    link = (
        f"{base_url}?receiver={YOOMONEY_WALLET}"
        f"&quickpay-form=shop"
        f"&targets={targets}"
        f"&paymentType=AC"        # прием с банковской карты
        f"&sum={amount}"
        f"&label={label}"
    )
    return link, label

def check_payment_received(label: str, amount: float) -> bool:
    """
    Запрашивает operation_history в ЮMoney и ищет операцию со статусом success и label=label.
    Проверяет, что сумма не меньше нужной (>= amount).
    Возвращает True, если платёж найден.
    """
    try:
        # Запрашиваем историю операций (до 30 последних)
        history = yoomoney_client.operation_history(records=30)

        # Получаем список операций
        operations = history.operations

        # Логируем для диагностики
        logging.info(f"Найдено операций: {len(operations)}")

        for op in operations:
            # Проверяем, есть ли атрибут `label` (не все операции имеют метку)
            op_label = getattr(op, "label", None)
            op_status = getattr(op, "status", None)
            op_amount = getattr(op, "amount", 0)

            logging.info(f"Проверяем операцию: Label={op_label}, Status={op_status}, Amount={op_amount}")

            # Сравниваем метку и статус
            if op_label == label and op_status == "success":
                # Проверяем, что сумма не меньше 45 (с учётом возможной комиссии)
                if float(op_amount) >= 45:
                    logging.info(f"✅ Оплата найдена: {op_label}, {op_status}, {op_amount}")
                    return True

        logging.info("❌ Оплата не найдена.")
        return False

    except Exception as e:
        logging.exception(f"Ошибка в check_payment_received: {e}")
        return False


# ============ Пример использования "router" (aiogram 3.x) ============
# Предполагаем, что router у вас уже создан. Если нет:
# from aiogram import Router
# router = Router()

from datetime import datetime, timedelta

# Словарь для хранения времени начала диалога
dialogue_start_times = {}

@router.callback_query(F.data == "consultation")
async def consultation_menu(call: CallbackQuery):
    """
    Обработка нажатия кнопки "Консультация".
    - Если пользователь уже воспользовался бесплатной, предлагаем оплату.
    - Иначе даём 1 бесплатный вопрос.
    """
    user_id = call.message.chat.id

    if user_id in free_consultation_used:
        # Уже использовал бесплатную — предлагаем оплату
        payment_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Оплатить 50 руб.",
                        callback_data="pay_consultation"
                    )
                ]
            ]
        )
        await call.message.answer(
            "Консультация платная. Для продолжения, пожалуйста, оплатите 50 рублей.",
            reply_markup=payment_keyboard
        )
        return

    # Еще не пользовался бесплатной консультацией
    free_consultation_used.add(user_id)

    await bot.send_chat_action(user_id, action='typing')
    await call.message.answer("⌛ Ищу специалиста...")
    await asyncio.sleep(10)

    await call.message.answer(
        "✅ Специалист найден! Напишите свой вопрос очень подробно, чтобы Таролог мог дать точный ответ."
    )
    user_queries[user_id] = None


@router.callback_query(F.data == "pay_consultation")
async def pay_consultation_handler(call: CallbackQuery):
    """
    Кнопка "Оплатить 50 руб." - генерируем ссылку Quick Pay, предлагаем оплатить,
    показываем кнопку "Я оплатил, проверить".
    """
    user_id = call.message.chat.id
    pay_link, label = create_yoomoney_quickpay_link(amount=50.0, user_id=user_id)

    # Сохраняем инфо, что этот user_id должен оплатить (label, amount)
    pending_payments[user_id] = {
        "label": label,
        "amount": 50.0
    }

    payment_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплатить через ЮMoney (50 руб.)",
                    url=pay_link
                )
            ],
            [
                InlineKeyboardButton(
                    text="Я оплатил, проверить",
                    callback_data="check_payment"
                )
            ]
        ]
    )
    await call.message.answer(
        "Для продолжения консультации, пожалуйста, оплатите 50 рублей по ссылке выше. "
        "Затем нажмите «Я оплатил, проверить».",
        reply_markup=payment_keyboard
    )

@router.callback_query(F.data == "check_payment")
async def check_payment_handler(call: CallbackQuery):
    """
    Кнопка "Я оплатил, проверить". Смотрим в pending_payments, 
    вызываем check_payment_received(...).
    """
    user_id = call.message.chat.id
    pay_info = pending_payments.get(user_id)
    if not pay_info:
        await call.message.answer("Нет данных о платеже для этого пользователя.")
        return

    label = pay_info["label"]
    amount = pay_info["amount"]

    paid = check_payment_received(label=label, amount=amount)
    if paid:
        await call.message.answer("Оплата подтверждена! Можете продолжить консультацию.")
        # Удаляем запись, чтобы не проверять повторно
        del pending_payments[user_id]
        if user_id in free_consultation_used:
            free_consultation_used.remove(user_id)
    else:
        await call.message.answer(
            "Оплата не найдена или не завершена. Убедитесь, что платеж прошёл, "
            "или попробуйте проверить ещё раз позже."
        )

@router.message(lambda m: m.chat.id in user_queries and user_queries[m.chat.id] is None)
async def receive_user_query(message: Message):
    """
    Первый бесплатный вопрос пользователя (до диалога).
    """
    user_id = message.chat.id
    query_text = message.text.strip() if message.text else ""

    if not query_text:
        await message.answer("❌ Ваш вопрос пуст. Пожалуйста, введите корректный запрос.")
        return

    user_queries[user_id] = query_text
    await message.answer("⌛ Ждем ответ специалиста...")
    await bot.send_chat_action(user_id, action='typing')
    await asyncio.sleep(3)

    # Здесь примеры для вашей гемини-модели (заглушка или реальный вызов)
    try:
        # Сформировали prompt (пример)
        system_prompt = ("Ты — профессиональный таролог ...\n\n")
        full_prompt = f"{system_prompt}Пользователь: {query_text}\nТаролог:"

        # Пример вызова к Gemini:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=full_prompt
        )
        if hasattr(response, 'text') and response.text:
            answer = response.text.strip()
        else:
            answer = "Я не смог получить ответ от специалиста. Попробуйте позже."

    except Exception as e:
        logging.exception(f"🚨 Ошибка при запросе к Gemini: {str(e)}")
        answer = "🚨 Ошибка при обработке запроса. Попробуйте позже."

    # Отправляем ответ
    await message.answer(f"🔮 Ответ специалиста:\n\n{answer}")

    # Сохраняем историю
    conversation_context[user_id] = [
        {"role": "user", "content": query_text},
        {"role": "assistant", "content": answer}
    ]

    # Предлагаем начать диалог
    dialog_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Начать диалог",
                    callback_data="start_dialog"
                )
            ]
        ]
    )
    await message.answer(
        "Если хотите продолжить диалог со специалистом, нажмите кнопку ниже.",
        reply_markup=dialog_keyboard
    )
    del user_queries[user_id]

@router.callback_query(F.data == "start_dialog")
async def start_dialog_handler(call: CallbackQuery):
    """
    Начинаем диалог. Будет действовать 30 минут.
    """
    user_id = call.message.chat.id
    
    # Инициализируем контекст диалога
    conversation_context[user_id] = []
    # Запоминаем время начала диалога
    dialogue_start_times[user_id] = datetime.now()
    
    logging.info(f"Диалог для пользователя {user_id} инициализирован.")

    end_dialog_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Завершить диалог",
                    callback_data="end_dialog"
                )
            ]
        ]
    )
    await call.message.answer(
        "Диалог начат. Пожалуйста, введите ваше сообщение. "
        "Чтобы завершить диалог раньше, нажмите кнопку ниже.",
        reply_markup=end_dialog_keyboard
    )

@router.message(lambda m: m.chat.id in conversation_context)
async def dialogue_message_handler(message: Message):
    """
    Обработка сообщений в диалоге. Диалог длится не более 30 минут.
    """
    user_id = message.chat.id
    user_msg = message.text.strip() if message.text else ""

    # Если пользователь отправил пустое сообщение
    if not user_msg:
        await message.answer("❌ Сообщение пусто. Пожалуйста, введите корректный текст.")
        return

    # Если по какой-то причине нет времени начала (например, диалог уже завершен)
    if user_id not in dialogue_start_times:
        await message.answer("Диалог неактивен. Начните новый диалог, если нужна консультация.")
        return
    
    # Проверяем, не истекли ли 30 минут
    start_time = dialogue_start_times[user_id]
    now = datetime.now()
    if now - start_time > timedelta(minutes=30):
        # Завершаем диалог
        await message.answer(
            "Диалог автоматически завершён, так как прошло более 30 минут с момента начала.\n"
            "Если потребуется помощь, вы можете начать новую консультацию."
        )
        # Очищаем данные
        del conversation_context[user_id]
        del dialogue_start_times[user_id]
        return

    # Если всё в порядке — продолжаем диалог
    conversation_context[user_id].append({"role": "user", "content": user_msg})

    await bot.send_chat_action(user_id, action='typing')
    await asyncio.sleep(2)

    try:
        base_prompt = ("Ты — профессиональный таролог ...\n\nДиалог:\n")
        dialogue_history = ""
        for msg in conversation_context[user_id]:
            if msg["role"] == "user":
                dialogue_history += f"Пользователь: {msg['content']}\n"
            else:
                dialogue_history += f"Специалист: {msg['content']}\n"

        full_prompt = f"{base_prompt}{dialogue_history}\nСпециалист:"
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=full_prompt
        )
        if hasattr(response, 'text') and response.text:
            answer = response.text.strip()
        else:
            answer = "Сейчас не могу ответить, попробуйте позднее."

    except Exception as e:
        logging.exception(f"🚨 Ошибка при запросе к Gemini (диалог): {str(e)}")
        answer = "🚨 Ошибка при обработке запроса. Попробуйте позже."

    # Добавляем ответ в контекст
    conversation_context[user_id].append({"role": "assistant", "content": answer})

    end_dialog_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Завершить диалог",
                    callback_data="end_dialog"
                )
            ]
        ]
    )

    await message.answer(
        f"🔮 Ответ специалиста:\n\n{answer}",
        reply_markup=end_dialog_keyboard
    )

@router.callback_query(F.data == "end_dialog")
async def end_dialog_handler(call: CallbackQuery):
    """
    Принудительное завершение диалога по нажатию кнопки.
    """
    user_id = call.message.chat.id
    
    # Удаляем контекст, если он есть
    if user_id in conversation_context:
        del conversation_context[user_id]
    
    if user_id in dialogue_start_times:
        del dialogue_start_times[user_id]

    logging.info(f"Диалог для пользователя {user_id} завершён, контекст удалён.")
    await call.message.answer(
        "Диалог завершен. Если потребуется помощь, вы можете начать новую консультацию."
    )

# ================== Точка входа ==================

async def main():
    """Главная асинхронная функция"""
    logging.info("🚀 Бот запускается...")

    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем роутер с обработчиками
    dp.include_router(router)

    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())