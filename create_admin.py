"""Run locally once to create an administrator. Never stores plaintext password."""
import getpass
import re
from db import Store
from security import hash_password
import psycopg


def main():
    username = input('Логин администратора: ').strip().lower()
    name = input('Имя: ').strip()
    password = getpass.getpass('Пароль (8-128 символов): ')
    if not re.fullmatch(r'[a-z0-9_]{3,50}', username) or not name or len(name) > 150:
        raise ValueError('Неверный логин или имя.')
    if not 8 <= len(password) <= 128:
        raise ValueError('Пароль должен содержать 8-128 символов.')
    if password != getpass.getpass('Повторите пароль: '):
        raise ValueError('Пароли не совпадают.')
    with Store().connect() as conn:
        conn.execute('INSERT INTO users(username,password_hash,full_name,role) VALUES (%s,%s,%s,%s)',
                     (username, hash_password(password), name, 'admin'))
    print('Администратор создан. Запустите python app.py')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, psycopg.Error) as error:
        print('Не удалось создать администратора:', error)
        raise SystemExit(1)
