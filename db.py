"""Database and application permissions. All user input uses SQL parameters."""
import os
import re
from pathlib import Path
from decimal import Decimal
import sqlite3
from contextlib import contextmanager
from security import hash_password, verify_password

ROOT = Path(__file__).resolve().parent


class Store:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv('SQLITE_PATH') or ROOT / 'data' / 'shop.sqlite3').expanduser()
        if not self.path.is_absolute():
            self.path = ROOT / self.path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            version = conn.execute('PRAGMA user_version').fetchone()[0]
            if version == 0:
                if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone():
                    raise ValueError('В файле уже есть неизвестные таблицы. Выберите новую базу через SQLITE_PATH.')
                statement = ''
                # Unlike executescript, execute preserves the outer transaction.
                for line in (ROOT / 'schema.sql').read_text(encoding='utf-8').splitlines(True):
                    statement += line
                    if sqlite3.complete_statement(statement):
                        conn.execute(statement)
                        statement = ''
                if statement.strip():
                    raise ValueError('Последний SQL-запрос не завершён.')
            elif version != 1:
                raise ValueError('Версия базы данных не поддерживается этой программой.')

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        conn.create_function('casefold', 1, lambda s: s.casefold() if s else '')
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def has_users(self):
        with self.connect() as conn:
            return conn.execute('SELECT 1 FROM users LIMIT 1').fetchone() is not None

    def create_first_admin(self, username, password, full_name):
        username = username.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,50}', username):
            raise ValueError('Логин: 3-50 латинских букв, цифр или знаков _.')
        if not 8 <= len(password) <= 128:
            raise ValueError('Пароль должен содержать от 8 до 128 символов.')
        if not full_name.strip() or len(full_name.strip()) > 150:
            raise ValueError('Укажите имя длиной до 150 символов.')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            if conn.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                raise ValueError('Первичная настройка уже выполнена. Войдите в существующий аккаунт.')
            conn.execute("INSERT INTO users(username,password_hash,full_name,role) VALUES (?,?,?,'admin')",
                         (username, hash_password(password), full_name.strip()))

    def authenticate(self, username, password):
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM users WHERE username=?', (username.strip().lower(),)).fetchone()
        if row and verify_password(password, row['password_hash']):
            row = dict(row)
            row.pop('password_hash')
            return row
        return None

    def register(self, username, password, full_name):
        username = username.strip().lower()
        if not re.fullmatch(r'[a-z0-9_]{3,50}', username):
            raise ValueError('Логин: 3-50 латинских букв, цифр или знаков _.')
        if not 8 <= len(password) <= 128:
            raise ValueError('Пароль должен содержать от 8 до 128 символов.')
        if not full_name.strip() or len(full_name.strip()) > 150:
            raise ValueError('Укажите имя, не длиннее 150 символов.')
        with self.connect() as conn:
            conn.execute('INSERT INTO users(username,password_hash,full_name) VALUES (?,?,?)',
                         (username, hash_password(password), full_name.strip()))

    def require_admin(self, conn, user_id):
        row = conn.execute('SELECT role FROM users WHERE id=?', (user_id,)).fetchone()
        if not row or row['role'] != 'admin':
            raise PermissionError('Действие доступно только администратору.')

    def references(self, kind):
        queries = {'categories': 'SELECT id,name FROM categories ORDER BY name',
                   'brands': 'SELECT id,name FROM brands ORDER BY name'}
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(queries[kind]).fetchall()]

    def products(self, search='', category=None, brand=None, low=0, high=None, available=False):
        from decimal import ROUND_CEILING, ROUND_FLOOR
        clauses, args = ['p.price_cents >= ?'], [int((Decimal(str(low)) * 100).to_integral_value(rounding=ROUND_CEILING))]
        if search.strip():
            # Unicode casefold supports Cyrillic, instr treats % and _ literally.
            clauses.append('instr(casefold(p.name),casefold(?)) > 0')
            args.append(search.strip())
        for field, value in [('category_id', category), ('brand_id', brand)]:
            if value is not None:
                clauses.append(f'p.{field}=?')
                args.append(value)
        if high is not None:
            clauses.append('p.price_cents <= ?')
            args.append(int((Decimal(str(high)) * 100).to_integral_value(rounding=ROUND_FLOOR)))
        if available:
            clauses.append('p.stock > 0')
        query = '''SELECT p.*, c.name AS category, b.name AS brand FROM products p
                   JOIN categories c ON c.id=p.category_id JOIN brands b ON b.id=p.brand_id
                   WHERE ''' + ' AND '.join(clauses) + ' ORDER BY casefold(p.name), p.id'
        with self.connect() as conn:
            rows = [dict(row) for row in conn.execute(query, args).fetchall()]
        for row in rows:
            row['price'] = Decimal(row['price_cents']) / 100
        return rows

    def specs(self, product_id):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute('SELECT name,value FROM product_specs WHERE product_id=? ORDER BY id',
                                (product_id,)).fetchall()]

    def save_product(self, user_id, product, specs, product_id=None):
        if not product['name'].strip() or len(product['name']) > 200:
            raise ValueError('Название товара не может быть пустым.')
        price = Decimal(str(product['price']))
        if not price.is_finite() or not 0 <= price <= Decimal('9999999999.99'):
            raise ValueError('Недопустимая цена.')
        if price * 100 != (price * 100).to_integral_value():
            raise ValueError('Цена может содержать не более двух знаков после запятой.')
        if not isinstance(product['stock'], int) or not 0 <= product['stock'] <= 2147483647:
            raise ValueError('Остаток должен быть целым неотрицательным числом.')
        names = [name.strip().casefold() for name, value in specs]
        if len(set(names)) != len(names):
            raise ValueError('Названия характеристик не должны повторяться.')
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.require_admin(conn, user_id)
            args = (product['name'].strip(), product['description'], int(price * 100),
                    product['stock'], product['category_id'], product['brand_id'])
            if product_id is None:
                product_id = conn.execute('''INSERT INTO products
                    (name,description,price_cents,stock,category_id,brand_id) VALUES (?,?,?,?,?,?)''', args).lastrowid
            else:
                result = conn.execute('''UPDATE products SET name=?,description=?,price_cents=?,
                    stock=?,category_id=?,brand_id=? WHERE id=?''', args + (product_id,))
                if result.rowcount != 1:
                    raise ValueError('Товар уже удалён. Обновите каталог.')
                conn.execute('DELETE FROM product_specs WHERE product_id=?', (product_id,))
            for name, value in specs:
                conn.execute('INSERT INTO product_specs(product_id,name,value) VALUES (?,?,?)',
                             (product_id, name.strip(), value.strip()))
        return product_id

    def delete_product(self, user_id, product_id):
        with self.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            self.require_admin(conn, user_id)
            conn.execute('DELETE FROM products WHERE id=?', (product_id,))

    def set_color(self, user_id, color):
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('Неверный формат цвета.')
        with self.connect() as conn:
            conn.execute('UPDATE users SET accent_color=? WHERE id=?', (color, user_id))
