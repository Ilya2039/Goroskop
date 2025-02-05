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

# Если нужно использовать Google Gemini:
# from google import genai
# gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ================== Константы / настройки ==================

API_TOKEN = '7582972873:AAGX0VJea8BdfGpV_QLvU3sBtXZi9L-xNrw'
TAROT_APP_URL = 'https://e04c-169-150-209-163.ngrok-free.app/tarot/'
NATAL_APP_URL = 'https://e04c-169-150-209-163.ngrok-free.app/natal/'
flask_url = "https://e04c-169-150-209-163.ngrok-free.app/horoscope/today"
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

def init_db():
    """Инициализация базы данных SQLite (синхронно, вызывается один раз при старте)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name, last_name):
    """Добавление пользователя в БД (синхронно)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, last_name))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Если пользователь уже существует
    
    conn.close()

''' Начало админки '''

ADMIN_IDS = [2089704895]

def get_user_count():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

@router.message(Command("stats"))
async def stats_command(message: Message):
    """Показывает количество пользователей в БД (доступно только админам)."""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом
    if user_id not in ADMIN_IDS:
        return
    
    # Если админ, выводим количество пользователей
    count = get_user_count()
    await message.answer(f"Количество пользователей в боте: {count}")

class MailingStates(StatesGroup):
    WAITING_FOR_TEXT = State()
    WAITING_FOR_CONFIRMATION = State()
    WAITING_FOR_BUTTON = State()

# Функция для получения списка user_id из БД
def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

@router.message(Command("mailing"))
async def start_mailing(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return  # Если не админ, игнорируем
    
    await message.answer("📢 Введите текст рассылки (или отправьте фото с подписью).")
    await state.set_state(MailingStates.WAITING_FOR_TEXT)  # Установили состояние "ждем текст"

# ------------------------------
# Хендлер, который ловит текст/фото при состоянии WAITING_FOR_TEXT
# ------------------------------
# Хендлер для обработки текста или фото
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

# Хендлер для обработки кнопки или пропуска
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

# Хендлер подтверждения рассылки
@router.message(StateFilter(MailingStates.WAITING_FOR_CONFIRMATION))
async def confirm_mailing(message: Message, state: FSMContext, bot: Bot):
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
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=button_text, url=button_url)]])

    await message.answer("📤 Начинаю рассылку...")
    
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
        await asyncio.sleep(0.1)

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

@router.callback_query(F.data == "consultation")
async def consultation_menu(call: CallbackQuery):
    """Запрос консультации"""
    user_id = call.message.chat.id

    # Показываем "печатает..." и отправляем сообщение
    await bot.send_chat_action(user_id, action='typing')
    await call.message.answer("⌛ Ищу специалиста...")

    # Теперь асинхронно "ждем" 10 секунд (пример), не блокируя других
    await asyncio.sleep(10)

    await call.message.answer("✅ Специалист найден! Напишите свой вопрос очень подробно, чтобы Таролог мог дать точный ответ.")
    user_queries[user_id] = None  # Фиксируем, что ждем первый вопрос

@router.message(lambda m: m.chat.id in user_queries and user_queries[m.chat.id] is None)
async def receive_user_query(message: Message):
    """Обработчик первого запроса пользователя для консультации"""
    user_id = message.chat.id
    query_text = message.text.strip() if message.text else ""
    
    if not query_text:
        await message.answer("❌ Ваш вопрос пуст. Пожалуйста, введите корректный запрос.")
        return

    user_queries[user_id] = query_text
    await message.answer("⌛ Ждем ответ специалиста...")
    await bot.send_chat_action(user_id, action='typing')

    # Эмуляция «ожидания» ответа 5 секунд
    await asyncio.sleep(20)

    # Пример системного prompt
    system_prompt = (
    "Ты — профессиональный таролог с многолетним опытом гадания на картах Таро. "
    "Ты толкуешь карты, используя традиционные расклады и глубокие знания эзотерики. "
    "Говори убедительно, таинственно, без лишних упоминаний про свободу воли или то, что итоговое решение за пользователем. "
    "Пиши, как настоящий мистик, который уверен в правдивости своих слов.\n\n"
    "🔮 **Как должен выглядеть твой ответ:**\n"
    "- Опиши, какие карты выпали (например, «Вам выпал Аркан ‘Суд’ в перевёрнутом положении…»).\n"
    "- Объясни значение карт в контексте заданного вопроса.\n"
    "- Определи, что карты говорят о прошлом, настоящем и будущем ситуации.\n"
    "- Дай осмысленные советы человеку, исходя из карт.\n"
    "- Если вопрос касается выбора (например, уйти с работы или остаться), укажи возможные сценарии.\n"
    "- Поддерживай **мистический, но при этом уверенный стиль ответа**.\n"
    "- Не перечисляй советы списками (без «1.» или «-»), не давай дисклеймеров и не упоминай «окончательное решение за вами».\n\n"
    "Если предоставленной информации недостаточно для точного предсказания, попроси пользователя рассказать подробнее о своей ситуации, "
    "уточнить детали или задать дополнительные вопросы, чтобы дать более точный прогноз.\n\n"
    "Учти, что это — диалог. Формируй ответы, опираясь на всю историю беседы, но избегай нумерованных пунктов. "
    "Пиши в одном потоке, используй мистические метафоры и эзотерические образы.\n\n"
    "Диалог:\n"
)
    
    full_prompt = (
        system_prompt
        + f"Пользователь: {query_text}\n"
        + "Таролог:"
    )

    try:
        # Пример вызова к Gemini:
        response = gemini_client.models.generate_content(
             model="gemini-2.0-flash-exp",
             contents=full_prompt
        )
        if hasattr(response, 'text') and response.text:
            answer = response.text.strip()
        else:
            answer = "Я не смог получить ответ от специалиста. Попробуйте позже."

        # Пока заглушка
        # answer = "🔮 [Пример ответа специалиста] Карты говорят, что ..."

        await message.answer(f"🔮 Ответ специалиста:\n\n{answer}")

        # Сохраняем историю диалога
        conversation_context[user_id] = [
            {"role": "user", "content": query_text},
            {"role": "assistant", "content": answer}
        ]

        # Клавиатура для начала полноценного диалога
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

    except Exception as e:
        logging.exception(f"🚨 Ошибка при запросе к Gemini: {str(e)}")
        await message.answer("🚨 Ошибка при обработке запроса. Попробуйте позже.")

    # Удаляем из user_queries, чтобы не мешало следующему первому вопросу
    del user_queries[user_id]

@router.callback_query(F.data == "start_dialog")
async def start_dialog_handler(call: CallbackQuery):
    user_id = call.message.chat.id
    if user_id not in conversation_context:
        conversation_context[user_id] = []
        logging.info(f"Диалог для пользователя {user_id} инициализирован (пуст).")

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
        "Чтобы завершить диалог, нажмите кнопку ниже.",
        reply_markup=end_dialog_keyboard
    )

@router.message(lambda m: m.chat.id in conversation_context)
async def dialogue_message_handler(message: Message):
    """Обработка сообщений, пока пользователь находится в диалоге."""
    user_id = message.chat.id
    user_msg = message.text.strip()

    if not user_msg:
        await message.answer("❌ Сообщение пусто. Пожалуйста, введите корректный текст.")
        return

    logging.info(f"Сообщение в диалоге от {user_id}: {user_msg}")

    # Добавляем в историю
    conversation_context[user_id].append({"role": "user", "content": user_msg})

    # Базовый промпт для диалога
    base_prompt = (
    "Ты — профессиональный таролог с многолетним опытом гадания на картах Таро. "
    "Ты толкуешь карты, используя традиционные расклады и глубокие знания эзотерики. "
    "Говори убедительно, таинственно, без лишних упоминаний про свободу воли или то, что итоговое решение за пользователем. "
    "Пиши, как настоящий мистик, который уверен в правдивости своих слов.\n\n"
    "🔮 **Как должен выглядеть твой ответ:**\n"
    "- Опиши, какие карты выпали (например, «Вам выпал Аркан ‘Суд’ в перевёрнутом положении…»).\n"
    "- Объясни значение карт в контексте заданного вопроса.\n"
    "- Определи, что карты говорят о прошлом, настоящем и будущем ситуации.\n"
    "- Дай осмысленные советы человеку, исходя из карт.\n"
    "- Если вопрос касается выбора (например, уйти с работы или остаться), укажи возможные сценарии.\n"
    "- Поддерживай **мистический, но при этом уверенный стиль ответа**.\n"
    "- Не перечисляй советы списками (без «1.» или «-»), не давай дисклеймеров и не упоминай «окончательное решение за вами».\n\n"
    "Если предоставленной информации недостаточно для точного предсказания, попроси пользователя рассказать подробнее о своей ситуации, "
    "уточнить детали или задать дополнительные вопросы, чтобы дать более точный прогноз.\n\n"
    "Учти, что это — диалог. Формируй ответы, опираясь на всю историю беседы, но избегай нумерованных пунктов. "
    "Пиши в одном потоке, используй мистические метафоры и эзотерические образы.\n\n"
    "Диалог:\n"
)

    # Собираем историю
    dialogue_history = ""
    for msg in conversation_context[user_id]:
        if msg["role"] == "user":
            dialogue_history += f"Пользователь: {msg['content']}\n"
        else:
            dialogue_history += f"Специалист: {msg['content']}\n"

    full_prompt = base_prompt + "\n\nИстория:\n" + dialogue_history

    await bot.send_chat_action(user_id, action='typing')

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=full_prompt
        )

        if hasattr(response, 'text') and response.text:
            answer = response.text.strip()
        else:
            answer = "Я не смог получить ответ от специалиста. Попробуйте позже."
        await asyncio.sleep(1)
        # answer = "🔮 [Пример ответа в диалоге] Я вижу, что карты указывают ..."

        # Сохраняем ответ
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

    except Exception as e:
        logging.exception(f"🚨 Ошибка при запросе к Gemini (диалог): {str(e)}")
        await message.answer("🚨 Ошибка при обработке запроса. Попробуйте позже.")

@router.callback_query(F.data == "end_dialog")
async def end_dialog_handler(call: CallbackQuery):
    user_id = call.message.chat.id
    if user_id in conversation_context:
        del conversation_context[user_id]
        logging.info(f"Диалог для пользователя {user_id} завершён, контекст удалён.")
    await call.message.answer("Диалог завершен. Если потребуется помощь, вы можете начать новую консультацию.")

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



