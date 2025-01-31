import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import sqlite3
import json  # ВАЖНО: для json.loads
import google.generativeai as genai  

# 🔹 Настройки
API_TOKEN = '7584759675:AAGMKdKTRMjaC0Rc1g-Ysw-5J2dlniIQdAA'
MINI_APP_URL = 'https://eb12-79-127-211-218.ngrok-free.app'  # Ссылка на мини-приложение
GEMINI_API_KEY = "AIzaSyCqE4taBEs1GJUh_pJQUqdGgcSEfGL8Pbc"  # Укажите ваш API-ключ Gemini


# 🔹 Инициализация бота и Gemini API
bot = telebot.TeleBot(API_TOKEN)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

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
        pass  
    conn.close()

# 🔹 Инициализируем базу данных
init_db()

# 🔹 Карты и их значения
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

# 🔹 Команда /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name

    add_user(user_id, username, first_name, last_name)

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔮 Выбрать карты Таро", web_app=WebAppInfo(url=MINI_APP_URL)))

    bot.send_message(
        chat_id=message.chat.id,
        text=f"Привет, {first_name}! Нажми на кнопку, чтобы запустить мини-приложение и выбрать свои карты таро:",
        reply_markup=keyboard
    )

# 🔹 Обработка нажатия кнопки "Перейти к раскладу"
@bot.message_handler(content_types=['web_app_data'])
def handle_web_app_data(message):
    user_id = message.chat.id

    try:
        # Декодируем JSON-данные от WebApp
        selected_cards_json = message.web_app_data.data
        selected_cards = json.loads(selected_cards_json)  

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

        selected_meanings = [tarot_meanings.get(num) for num in numbers if tarot_meanings.get(num)]
        if len(selected_meanings) != 3:
            bot.send_message(user_id, "❌ Ошибка в определении карт.")
            return

        # 🔹 Отправляем запрос в Gemini по каждой карте и отправляем три отдельных сообщения
        for meaning in selected_meanings:
            query = f"Человеку выпала карта {meaning}. Дай предсказание, какое значение это может иметь? Ответ до 500 символов."
            try:
                response = model.generate_content(query)
                if hasattr(response, "text") and response.text:
                    prediction = response.text.strip()
                else:
                    prediction = "❌ Gemini не дал ответа."
            except Exception as e:
                print("❌ Ошибка при запросе к Gemini:", e)
                prediction = "🚨 Ошибка при запросе к Gemini."

            bot.send_message(user_id, f"🔮 Карта: {meaning}\n✨ {prediction}")

    except Exception as e:
        print("❌ Ошибка обработки web_app_data:", e)
        bot.send_message(user_id, "❌ Невозможно обработать данные от мини-приложения.")

# 🔹 Запуск бота
if __name__ == '__main__':
    print("🚀 Бот запущен...")
    bot.polling(none_stop=True)
