import psycopg2
from config import POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
import logging

def get_connection():
    return psycopg2.connect(
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT
    )

def init_db(): 
    """
    Инициализация базы данных PostgreSQL (синхронно, вызывается один раз при старте).
    Создает таблицу users, если её нет.
    Добавляет новое поле consultation_credits, если его не было.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Создаем таблицу, если её нет
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            free_consultation_used BOOLEAN NOT NULL DEFAULT FALSE,
            balance NUMERIC(10,2) NOT NULL DEFAULT 0.00,
            consultation_credits INTEGER NOT NULL DEFAULT 0,  -- Новое поле
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Проверяем, есть ли уже поле consultation_credits, если нет — добавляем
    cursor.execute("""
    ALTER TABLE users ADD COLUMN IF NOT EXISTS consultation_credits INTEGER NOT NULL DEFAULT 0;
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

def get_consultation_credits(user_id: int) -> int:
    """Возвращает количество доступных консультаций у пользователя."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT consultation_credits FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else 0

def decrement_consultation_credits(user_id: int):
    """Уменьшает количество доступных консультаций на 1 (если они есть)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET consultation_credits = consultation_credits - 1 WHERE user_id = %s AND consultation_credits > 0", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()

def add_consultation_credits(user_id: int, credits: int):
    """Добавляет пользователю указанное количество консультаций."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET consultation_credits = consultation_credits + %s WHERE user_id = %s", (credits, user_id))
    conn.commit()
    cursor.close()
    conn.close()