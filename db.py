"""Database and application permissions. All user input uses SQL parameters."""
import os
import re
from pathlib import Path
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from security import hash_password, verify_password

load_dotenv(Path(__file__).with_name('.env'))


class Store:
    def connect(self):
        return psycopg.connect(
            host=os.getenv('DB_HOST', '127.0.0.1'),
            port=int(os.getenv('DB_PORT', '5432')),
            dbname=os.getenv('DB_NAME', 'electronics_shop'),
            user=os.getenv('DB_USER', 'electronics_app'),
            password=os.getenv('DB_PASSWORD', ''),
            connect_timeout=5, row_factory=dict_row,
        )

    def authenticate(self, username, password):
        with self.connect() as conn:
            row = conn.execute('SELECT * FROM users WHERE username=%s', (username.strip().lower(),)).fetchone()
        if row and verify_password(password, row['password_hash']):
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
            conn.execute('INSERT INTO users(username,password_hash,full_name) VALUES (%s,%s,%s)',
                         (username, hash_password(password), full_name.strip()))

    def require_admin(self, conn, user_id):
        row = conn.execute('SELECT role FROM users WHERE id=%s', (user_id,)).fetchone()
        if not row or row['role'] != 'admin':
            raise PermissionError('Действие доступно только администратору.')

    def references(self, kind):
        queries = {'categories': 'SELECT id,name FROM categories ORDER BY name',
                   'brands': 'SELECT id,name FROM brands ORDER BY name'}
        with self.connect() as conn:
            return conn.execute(queries[kind]).fetchall()

    def products(self, search='', category=None, brand=None, low=0, high=None, available=False):
        clauses, args = ['p.price >= %s'], [low]
        if search.strip():
            # Treat %, _ and backslashes as literal search characters.
            pattern = search.strip().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            clauses.append('p.name ILIKE %s')
            args.append('%' + pattern + '%')
        for field, value in [('category_id', category), ('brand_id', brand)]:
            if value is not None:
                clauses.append(f'p.{field}=%s')
                args.append(value)
        if high is not None:
            clauses.append('p.price <= %s')
            args.append(high)
        if available:
            clauses.append('p.stock > 0')
        query = '''SELECT p.*, c.name AS category, b.name AS brand FROM products p
                   JOIN categories c ON c.id=p.category_id JOIN brands b ON b.id=p.brand_id
                   WHERE ''' + ' AND '.join(clauses) + ' ORDER BY p.name, p.id'
        with self.connect() as conn:
            return conn.execute(query, args).fetchall()

    def specs(self, product_id):
        with self.connect() as conn:
            return conn.execute('SELECT name,value FROM product_specs WHERE product_id=%s ORDER BY id',
                                (product_id,)).fetchall()

    def save_product(self, user_id, product, specs, product_id=None):
        if not product['name'].strip():
            raise ValueError('Название товара не может быть пустым.')
        if Decimal(str(product['price'])) < 0 or product['stock'] < 0:
            raise ValueError('Цена и остаток не могут быть отрицательными.')
        names = [name.casefold() for name, value in specs]
        if len(set(names)) != len(names):
            raise ValueError('Названия характеристик не должны повторяться.')
        with self.connect() as conn:
            self.require_admin(conn, user_id)
            args = tuple(product[k] for k in ('name', 'description', 'price', 'stock', 'category_id', 'brand_id'))
            if product_id is None:
                product_id = conn.execute('''INSERT INTO products
                    (name,description,price,stock,category_id,brand_id) VALUES (%s,%s,%s,%s,%s,%s)
                    RETURNING id''', args).fetchone()['id']
            else:
                result = conn.execute('''UPDATE products SET name=%s,description=%s,price=%s,
                    stock=%s,category_id=%s,brand_id=%s WHERE id=%s''', args + (product_id,))
                if result.rowcount != 1:
                    raise ValueError('Товар уже удалён. Обновите каталог.')
                conn.execute('DELETE FROM product_specs WHERE product_id=%s', (product_id,))
            for name, value in specs:
                conn.execute('INSERT INTO product_specs(product_id,name,value) VALUES (%s,%s,%s)',
                             (product_id, name.strip(), value.strip()))
        return product_id

    def delete_product(self, user_id, product_id):
        with self.connect() as conn:
            self.require_admin(conn, user_id)
            conn.execute('DELETE FROM products WHERE id=%s', (product_id,))

    def set_color(self, user_id, color):
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('Неверный формат цвета.')
        with self.connect() as conn:
            conn.execute('UPDATE users SET accent_color=%s WHERE id=%s', (color, user_id))
