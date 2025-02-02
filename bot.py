import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import sqlite3
import json  # Для обработки данных из Web App
from google import genai
import requests
import logging
# from googletrans import Translator
from datetime import datetime
# from google.cloud import translate_v2 as translate
from translatepy import Translator

# 🔹 Настройки
API_TOKEN = '7582972873:AAGX0VJea8BdfGpV_QLvU3sBtXZi9L-xNrw'
TAROT_APP_URL = 'https://408b-79-127-211-218.ngrok-free.app/tarot/'
NATAL_APP_URL = 'https://408b-79-127-211-218.ngrok-free.app/natal/'
flask_url = "https://408b-79-127-211-218.ngrok-free.app/horoscope/today"
GEMINI_API_KEY = "AIzaSyCqE4taBEs1GJUh_pJQUqdGgcSEfGL8Pbc"

# 🔹 Инициализация бота и Gemini API
bot = telebot.TeleBot(API_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
translator = Translator()

# 🔹 Логирование
logging.basicConfig(level=logging.DEBUG)

# 🔹 База данных SQLite
DB_NAME = "users.db"

def init_db():
    """Инициализация базы данных"""
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
    """Добавление пользователя в базу данных"""
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

# 🔹 Инициализируем базу данных
init_db()

# 🔹 Команда /start
@bot.message_handler(commands=['start'])
def start_command(message):
    """Главное меню"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Добавляем пользователя в БД
    add_user(user_id, username, first_name, last_name)

    # Клавиатура с кнопками
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔮 Сделать расклад Таро", web_app=WebAppInfo(url=TAROT_APP_URL)))
    keyboard.add(InlineKeyboardButton("🌌 Получить натальную карту", web_app=WebAppInfo(url=NATAL_APP_URL)))
    keyboard.add(InlineKeyboardButton("✨ Гороскоп", callback_data="horoscope"))

    # Отправляем сообщение с кнопками
    bot.send_message(
        chat_id=message.chat.id,
        text="Привет! Выберите, что вы хотите сделать:",
        reply_markup=keyboard
    )

'''# 🔹 Обработчик нажатия на кнопку "Гороскоп"
@bot.callback_query_handler(func=lambda call: call.data == "horoscope")
def horoscope_menu(call):
    """Меню выбора типа гороскопа"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🌞 Дневной гороскоп", callback_data="daily_horoscope"))
    keyboard.add(InlineKeyboardButton("❤️ Любовный гороскоп", callback_data="love_horoscope"))
    keyboard.add(InlineKeyboardButton("💼 Карьерный гороскоп", callback_data="career_horoscope"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Какой гороскоп хотите?",
        reply_markup=keyboard
    )'''

zodiac_translation = {
    "Овен": "Aries", "Телец": "Taurus", "Близнецы": "Gemini", "Рак": "Cancer",
    "Лев": "Leo", "Дева": "Virgo", "Весы": "Libra", "Скорпион": "Scorpio",
    "Стрелец": "Sagittarius", "Козерог": "Capricorn", "Водолей": "Aquarius", "Рыбы": "Pisces"
}

# 🔹 Меню выбора типа гороскопа
@bot.callback_query_handler(func=lambda call: call.data == "horoscope")
def horoscope_menu(call):
    """Меню выбора типа гороскопа"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🌞 Дневной гороскоп", callback_data="daily_horoscope"))
    keyboard.add(InlineKeyboardButton("❤️ Любовный гороскоп", callback_data="love_horoscope"))
    keyboard.add(InlineKeyboardButton("💼 Карьерный гороскоп", callback_data="career_horoscope"))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Какой гороскоп хотите?",
        reply_markup=keyboard
    )

# 🔹 Обработчик выбора типа гороскопа
@bot.callback_query_handler(func=lambda call: call.data in ["daily_horoscope", "love_horoscope", "career_horoscope"])
def select_zodiac(call):
    """Меню выбора знака зодиака"""
    horoscope_type_full = call.data  

    zodiac_signs = list(zodiac_translation.keys())

    keyboard = InlineKeyboardMarkup()
    for sign in zodiac_signs:
        keyboard.add(InlineKeyboardButton(sign, callback_data=f"{horoscope_type_full}_{sign}"))

    # Отображаем выбранный тип гороскопа
    horoscope_texts_ru = {
        "daily_horoscope": "дневной гороскоп",
        "love_horoscope": "любовный гороскоп",
        "career_horoscope": "карьерный гороскоп"
    }
    display_text = horoscope_texts_ru.get(horoscope_type_full, "гороскоп")

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Вы выбрали {display_text}. Теперь выберите ваш знак зодиака:",
        reply_markup=keyboard
    )

# 🔹 Обработчик выбора знака зодиака и запроса в Gemini
@bot.callback_query_handler(func=lambda call: any(call.data.startswith(t) for t in ['daily_', 'love_', 'career_']))
def handle_zodiac_choice(call):
    user_id = call.message.chat.id
    type_full, zodiac_sign = call.data.rsplit('_', 1)
    horoscope_type = type_full.split('_')[0]  

    # Словарь для отображения типа гороскопа на русском
    horoscope_texts_ru = {
        'daily': 'дневной гороскоп',
        'love': 'любовный гороскоп',
        'career': 'карьерный гороскоп'
    }

    # Проверяем, что выбранный тип гороскопа корректный
    if horoscope_type not in horoscope_texts_ru:
        bot.send_message(user_id, "❌ Ошибка: неверный тип гороскопа.")
        return

    # Формируем запрос к Gemini на русском языке
    from datetime import datetime
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

    # Выбираем нужный промпт в зависимости от типа гороскопа
    query_ru = horoscope_prompts[horoscope_type]

    logging.info(f"📨 Отправка запроса в Gemini: {query_ru}")

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
        bot.send_message(user_id, f"🔮 {horoscope_russian}")

    except Exception as e:
        logging.exception(f"🚨 Ошибка при запросе гороскопа: {str(e)}")
        bot.send_message(user_id, "🚨 Ошибка при запросе гороскопа. Попробуйте позже.")
        
# 🔹 Запуск бота
if __name__ == '__main__':
    print("🚀 Бот запущен...")
    bot.polling(none_stop=True)



