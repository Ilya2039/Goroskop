import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import sqlite3

API_TOKEN = '7584759675:AAGMKdKTRMjaC0Rc1g-Ysw-5J2dlniIQdAA'
MINI_APP_URL = 'https://18b3-185-77-216-6.ngrok-free.app'  # Ссылка на мини-приложение

# Инициализация бота
bot = telebot.TeleBot(API_TOKEN)

# Функции для работы с базой данных
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
        # Если пользователь уже существует
        pass
    
    conn.close()

# Инициализируем базу данных
init_db()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    # Получаем данные пользователя
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    # Добавляем пользователя в базу данных
    add_user(user_id, username, first_name, last_name)

    # Создаём кнопку с WebApp
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎲 Бросить кубик!", web_app=WebAppInfo(url=MINI_APP_URL)))

    # Отправляем сообщение с кнопкой
    bot.send_message(
        chat_id=message.chat.id,
        text=f"Привет, {first_name}! Нажми на кнопку, чтобы запустить мини-приложение:",
        reply_markup=keyboard
    )

# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.polling(none_stop=True)

