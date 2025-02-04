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
import time

# 🔹 Настройки
API_TOKEN = '7582972873:AAGX0VJea8BdfGpV_QLvU3sBtXZi9L-xNrw'
TAROT_APP_URL = 'https://e04c-169-150-209-163.ngrok-free.app/tarot/'
NATAL_APP_URL = 'https://e04c-169-150-209-163.ngrok-free.app/natal/'
flask_url = "https://e04c-169-150-209-163.ngrok-free.app/horoscope/today"
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
    keyboard.add(InlineKeyboardButton("✨ Консультация Таролога", callback_data="consultation"))

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

user_queries = {}           # Для первоначального запроса консультации
conversation_context = {}

# ========= Обработчик запроса консультации =========
@bot.callback_query_handler(func=lambda call: call.data == "consultation")
def consultation_menu(call):
    """Запрос консультации"""
    user_id = call.message.chat.id

    # Отправляем сообщение с индикатором загрузки
    bot.send_chat_action(user_id, action='typing')  # Показываем "печатает..."
    bot.send_message(user_id, "⌛ Ищу специалиста...")

    time.sleep(10)  # Эмулируем поиск специалиста

    # Отправляем финальное сообщение после ожидания
    bot.send_message(user_id, "✅ Специалист найден! Напишите свой вопрос.")

    user_queries[user_id] = None  # Фиксируем ожидание запроса

# ========= Обработчик ввода первого запроса пользователя =========
@bot.message_handler(func=lambda message: message.chat.id in user_queries and user_queries[message.chat.id] is None)
def receive_user_query(message):
    user_id = message.chat.id
    query_text = message.text.strip() if message.text else ""
    
    if not query_text:
        bot.send_message(user_id, "❌ Ваш вопрос пуст. Пожалуйста, введите корректный запрос.")
        return

    # Сохраняем запрос пользователя
    user_queries[user_id] = query_text

    bot.send_message(user_id, "⌛ Ждем ответ специалиста...")
    bot.send_chat_action(user_id, action='typing')

    time.sleep(20)  # Симуляция ожидания ответа

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


    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=system_prompt
        )

        if hasattr(response, 'text') and response.text:
            answer = response.text.strip()
        else:
            answer = "Я не смог получить ответ от специалиста. Попробуйте позже."

        bot.send_message(user_id, f"🔮 Ответ специалиста:\n\n{answer}")

        # **Сохраняем первоначальный вопрос в контексте диалога**
        conversation_context[user_id] = [{"role": "user", "content": query_text}]

        markup = telebot.types.InlineKeyboardMarkup()
        start_dialog_button = telebot.types.InlineKeyboardButton(text="Начать диалог", callback_data="start_dialog")
        markup.add(start_dialog_button)
        bot.send_message(user_id, "Если хотите продолжить диалог с специалистом, нажмите кнопку ниже.", reply_markup=markup)

    except Exception as e:
        logging.exception(f"🚨 Ошибка при запросе к Gemini: {str(e)}")
        bot.send_message(user_id, "🚨 Ошибка при обработке запроса. Попробуйте позже.")

    del user_queries[user_id]

# ========= Обработчик нажатия кнопки "Начать диалог" =========
@bot.callback_query_handler(func=lambda call: call.data == "start_dialog")
def start_dialog_handler(call):
    user_id = call.message.chat.id
    # Инициализируем контекст диалога для пользователя (сохраняем историю сообщений)
    if user_id not in conversation_context:
        conversation_context[user_id] = []  # начинаем с пустого контекста
    logging.info(f"Диалог для пользователя {user_id} запущен. Инициализирован пустой контекст.")
    
    # Предлагаем ввести первое сообщение в диалоге и показываем кнопку для завершения диалога
    markup = telebot.types.InlineKeyboardMarkup()
    end_dialog_button = telebot.types.InlineKeyboardButton(text="Завершить диалог", callback_data="end_dialog")
    markup.add(end_dialog_button)
    bot.send_message(user_id,
                     "Диалог начат. Пожалуйста, введите ваше сообщение. "
                     "Чтобы завершить диалог, нажмите кнопку ниже.",
                     reply_markup=markup)

# ========= Обработчик сообщений в режиме диалога =========
@bot.message_handler(func=lambda message: message.chat.id in conversation_context and message.content_type == 'text')
def dialogue_message_handler(message):
    user_id = message.chat.id
    user_msg = message.text.strip()
    
    logging.info(f"Получено сообщение в диалоге от пользователя {user_id}: {user_msg}")
    
    if not user_msg:
        bot.send_message(user_id, "❌ Сообщение пусто. Пожалуйста, введите корректный текст.")
        return

    # Добавляем сообщение пользователя в контекст
    conversation_context[user_id].append({"role": "user", "content": user_msg})

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


    # Собираем историю сообщений
    dialogue_history = ""
    for msg in conversation_context[user_id]:
        if msg["role"] == "user":
            dialogue_history += f"Пользователь: {msg['content']}\n"
        else:
            dialogue_history += f"Специалист: {msg['content']}\n"

    full_prompt = base_prompt + dialogue_history

    bot.send_chat_action(user_id, action='typing')

    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=full_prompt
        )

        if hasattr(response, 'text') and response.text:
            answer = response.text.strip()
        else:
            answer = "Я не смог получить ответ от специалиста. Попробуйте позже."

        # Добавляем ответ специалиста в контекст диалога
        conversation_context[user_id].append({"role": "assistant", "content": answer})
        logging.info(f"Ответ специалиста для пользователя {user_id}: {answer}")

        # Отправляем ответ вместе с кнопкой для завершения диалога
        markup = telebot.types.InlineKeyboardMarkup()
        end_dialog_button = telebot.types.InlineKeyboardButton(text="Завершить диалог", callback_data="end_dialog")
        markup.add(end_dialog_button)
        bot.send_message(user_id, f"🔮 Ответ специалиста:\n\n{answer}", reply_markup=markup)

    except Exception as e:
        logging.exception(f"🚨 Ошибка при запросе к Gemini в режиме диалога: {str(e)}")
        bot.send_message(user_id, "🚨 Ошибка при обработке запроса. Попробуйте позже.")

# ========= Обработчик нажатия кнопки "Завершить диалог" =========
@bot.callback_query_handler(func=lambda call: call.data == "end_dialog")
def end_dialog_handler(call):
    user_id = call.message.chat.id
    if user_id in conversation_context:
        del conversation_context[user_id]
        logging.info(f"Диалог для пользователя {user_id} завершён и контекст удалён.")
    bot.send_message(user_id, "Диалог завершен. Если потребуется помощь, вы можете начать новую консультацию.")


# 🔹 Запуск бота
if __name__ == '__main__':
    print("🚀 Бот запущен...")
    bot.polling(none_stop=True)



