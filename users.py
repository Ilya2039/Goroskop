import sqlite3

DB_NAME = "users.db"

def view_users():
    """Вывод списка пользователей"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    print("Список пользователей:")
    for user in users:
        print(f"ID: {user[0]}, User ID: {user[1]}, Username: {user[2]}, First Name: {user[3]}, Last Name: {user[4]}, Date Added: {user[5]}")

    conn.close()

if __name__ == "__main__":
    view_users()