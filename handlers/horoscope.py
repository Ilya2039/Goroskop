import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import GEMINI_API_KEY
from google import genai

router = Router()
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

zodiac_translation = {
    "Овен": "Aries", "Телец": "Taurus", "Близнецы": "Gemini", "Рак": "Cancer",
    "Лев": "Leo", "Дева": "Virgo", "Весы": "Libra", "Скорпион": "Scorpio",
    "Стрелец": "Sagittarius", "Козерог": "Capricorn", "Водолей": "Aquarius", "Рыбы": "Pisces"
}

@router.callback_query(F.data == "horoscope")
async def horoscope_menu(call: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌞 Дневной гороскоп", callback_data="daily_horoscope")],
            [InlineKeyboardButton(text="❤️ Любовный гороскоп", callback_data="love_horoscope")],
            [InlineKeyboardButton(text="💼 Карьерный гороскоп", callback_data="career_horoscope")]
        ]
    )
    await call.message.edit_text("Какой гороскоп хотите?", reply_markup=keyboard)

@router.callback_query(lambda c: c.data in ["daily_horoscope", "love_horoscope", "career_horoscope"])
async def select_zodiac(call: CallbackQuery):
    horoscope_type_full = call.data
    zodiac_signs = list(zodiac_translation.keys())
    rows = [[InlineKeyboardButton(text=sign, callback_data=f"{horoscope_type_full}_{sign}")] for sign in zodiac_signs]
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    horoscope_texts_ru = {
        "daily_horoscope": "дневной гороскоп",
        "love_horoscope": "любовный гороскоп",
        "career_horoscope": "карьерный гороскоп"
    }
    display_text = horoscope_texts_ru.get(horoscope_type_full, "гороскоп")
    await call.message.edit_text(f"Вы выбрали {display_text}. Теперь выберите ваш знак зодиака:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data.startswith("daily_") or c.data.startswith("love_") or c.data.startswith("career_"))
async def handle_zodiac_choice(call: CallbackQuery):
    user_id = call.message.chat.id
    type_full, zodiac_sign = call.data.rsplit('_', 1)
    horoscope_type = type_full.split('_')[0]
    await call.message.edit_reply_markup(reply_markup=None)
    today_date = datetime.now().strftime("%Y-%m-%d")
    '''horoscope_prompts = {
        'daily': f"Дай мне дневной гороскоп для {zodiac_sign} на {today_date}. Не пиши, что такого гороскопа нет.",
        'love': f"Дай мне любовный гороскоп для {zodiac_sign} на {today_date}. Не пиши, что такого гороскопа нет.",
        'career': f"Дай мне карьерный гороскоп для {zodiac_sign} на {today_date}. Не пиши, что такого гороскопа нет."
    }'''
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
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=query_ru
        )
        horoscope_russian = response.text.strip() if hasattr(response, 'text') and response.text else "Я не смог сгенерировать гороскоп сейчас. Попробуйте позже."
        logging.info(f"✅ Ответ от Gemini: {horoscope_russian}")
        await call.message.answer("🔮")
        await call.message.answer(f"🔮 {horoscope_russian}")
    except Exception as e:
        logging.exception(f"🚨 Ошибка при запросе гороскопа: {str(e)}")
        await call.message.answer("🚨 Ошибка при запросе гороскопа. Попробуйте позже.")