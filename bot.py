import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import sqlite3
import json  # Для обработки данных из Web App
from google import genai

# 🔹 Настройки
API_TOKEN = '7584759675:AAGMKdKTRMjaC0Rc1g-Ysw-5J2dlniIQdAA'
TAROT_APP_URL = 'https://9d18-79-127-211-218.ngrok-free.app/tarot/'  # Ссылка на приложение Таро
NATAL_APP_URL = 'https://9d18-79-127-211-218.ngrok-free.app/natal/'  # Ссылка на приложение Натальной карты
HOROSCOPE_APP_URL = 'https://9d18-79-127-211-218.ngrok-free.app/horoscope/'  # Замените на актуальный ngrok URL
GEMINI_API_KEY = "AIzaSyCqE4taBEs1GJUh_pJQUqdGgcSEfGL8Pbc"  # API-ключ Gemini

# 🔹 Инициализация бота и Gemini API
bot = telebot.TeleBot(API_TOKEN)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

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

# 🔹 Карты Таро и их значения
tarot_meanings = {
    1: "Огонь",
    2: "Вода",
    3: "Земля",
    4: "Воздух",
    5: "Сила",
    6: "Мудрость",
    7: "Любовь",
    8: "Дом"
}

# Словарь для хранения выбранных карт пользователей
user_cards = {}

# 🔹 Команда /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Добавляем пользователя в БД
    add_user(user_id, username, first_name, last_name)

    # Создаем кнопки для выбора между двумя приложениями
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔮 Сделать расклад Таро", web_app=WebAppInfo(url=TAROT_APP_URL)))
    keyboard.add(InlineKeyboardButton("🌌 Получить натальную карту", web_app=WebAppInfo(url=NATAL_APP_URL)))
    keyboard.add(InlineKeyboardButton("✨ Гороскоп", web_app=WebAppInfo(url=HOROSCOPE_APP_URL)))


    # Отправляем сообщение с кнопками
    bot.send_message(
        chat_id=message.chat.id,
        text="Привет! Выберите, что вы хотите сделать:",
        reply_markup=keyboard
    )

# 🔹 Обработчик данных из Web App
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    user_id = message.chat.id

    try:
        # Данные, пришедшие из tg.sendData(...) (JSON-строка)
        selected_cards_json = message.web_app_data.data
        selected_cards = json.loads(selected_cards_json)

        # Преобразуем имена файлов в номера карт
        numbers = []
        for filename in selected_cards:
            num_str = filename.replace("Таро", "").replace(".jpg", "")
            try:
                num = int(num_str)
                numbers.append(num)
            except:
                pass

        if len(numbers) != 3:
            bot.send_message(user_id, "❌ Не удалось определить выбранные карты.")
            return

        # Получаем значения карт
        selected_meanings = [tarot_meanings.get(num) for num in numbers if tarot_meanings.get(num)]

        if len(selected_meanings) != 3:
            bot.send_message(user_id, "❌ Ошибка в определении карт.")
            return

        # Формируем запрос в Gemini
        query = (
            f"Карты таро показали человеку {', '.join(selected_meanings)}. "
            f"Какое значение это может иметь? Дай ответ до 800 символов."
        )

        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=query
            )

            answer = response.text.strip() if hasattr(response, "text") and response.text else "❌ Gemini не дал понятного ответа."

            # Отправляем ответ пользователю
            bot.send_message(
                chat_id=user_id,
                text=f"📜 Твои карты: {', '.join(selected_meanings)}\n\n✨ Ответ от Gemini:\n{answer}"
            )

        except Exception as e:
            bot.send_message(
                chat_id=user_id,
                text="🚨 Ошибка при запросе к Gemini. Попробуйте позже."
            )

    except Exception as e:
        bot.send_message(user_id, "❌ Невозможно обработать данные от мини-приложения.")

# 🔹 Запуск бота
if __name__ == '__main__':
    print("🚀 Бот запущен...")
    bot.polling(none_stop=True)


