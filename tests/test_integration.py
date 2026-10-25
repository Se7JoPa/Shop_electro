"""Integration checks on a real temporary SQLite file, isolated from user data."""
import tempfile
from pathlib import Path
import unittest
from decimal import Decimal
from uuid import uuid4
from db import Store
from security import hash_password
import sqlite3


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.store = Store(Path(cls.temp.name) / 'test.sqlite3')
        cls.tag = 'test_' + uuid4().hex[:12]
        with cls.store.connect() as conn:
            cls.admin = conn.execute('''INSERT INTO users(username,password_hash,full_name,role)
                VALUES (?,?,?,'admin') RETURNING id''',
                (cls.tag, hash_password('password123'), 'Тест администратор')).fetchone()['id']
        cls.customer_login = cls.tag + '_buyer'
        cls.store.register(cls.customer_login, 'password123', 'Тест покупатель')
        cls.customer = cls.store.authenticate(cls.customer_login, 'password123')['id']
        cls.category = cls.store.references('categories')[0]['id']
        cls.brand = cls.store.references('brands')[0]['id']
        cls.product = dict(name=cls.tag + ' 100%_товар', description='Тест',
                           price=Decimal('123.45'), stock=3,
                           category_id=cls.category, brand_id=cls.brand)

    @classmethod
    def tearDownClass(cls):
        with cls.store.connect() as conn:
            conn.execute('DELETE FROM products WHERE name LIKE ?', (cls.tag + '%',))
            conn.execute('DELETE FROM users WHERE id IN (?,?)', (cls.admin, cls.customer))
        cls.temp.cleanup()

    def test_authentication(self):
        self.assertIsNone(self.store.authenticate(self.customer_login, 'wrong'))
        self.assertIsNone(self.store.authenticate("' OR 1=1 --", 'password123'))
        self.assertEqual(self.store.authenticate(self.customer_login, 'password123')['role'], 'customer')
        with self.assertRaises(ValueError):
            self.store.register('ab', 'short', 'Имя')

    def test_permission_enforced(self):
        with self.assertRaises(PermissionError):
            self.store.save_product(self.customer, self.product, [])
        with self.assertRaises(PermissionError):
            self.store.delete_product(self.customer, -1)

    def test_crud_filters_and_cascade(self):
        item_id = self.store.save_product(self.admin, self.product, [('Память', '128 ГБ')])
        try:
            rows = self.store.products('100%_', self.category, self.brand, 123, 124, True)
            self.assertIn(item_id, [row['id'] for row in rows])
            self.assertNotIn(item_id, [r['id'] for r in self.store.products(self.tag, low=200)])
            changed = dict(self.product, price=Decimal('150.25'), stock=0)
            self.store.save_product(self.admin, changed, [('Цвет', 'Синий')], item_id)
            self.assertEqual(self.store.specs(item_id)[0]['name'], 'Цвет')
            self.assertEqual(self.store.products(self.tag)[0]['price'], Decimal('150.25'))
            self.assertEqual(self.store.products(self.tag, available=True), [])
            self.store.delete_product(self.admin, item_id)
            self.assertEqual(self.store.specs(item_id), [])
            self.assertEqual(self.store.products(self.tag), [])
        finally:
            self.store.delete_product(self.admin, item_id)

    def test_failed_update_rolls_back(self):
        item_id = self.store.save_product(self.admin, self.product, [('Цвет', 'Красный')])
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                self.store.save_product(self.admin, dict(self.product, name='changed'), [('Цвет', '')], item_id)
            self.assertEqual(self.store.specs(item_id)[0]['value'], 'Красный')
            self.assertEqual(self.store.products(self.tag)[0]['name'], self.product['name'])
        finally:
            self.store.delete_product(self.admin, item_id)

    def test_color_persists(self):
        self.store.set_color(self.customer, '#7047eb')
        self.assertEqual(self.store.authenticate(self.customer_login, 'password123')['accent_color'], '#7047eb')
        with self.assertRaises(ValueError):
            self.store.set_color(self.customer, 'red; malicious')

    def test_russian_search_and_exact_money(self):
        product = dict(self.product, name=self.tag + ' НоУтБуК', price=Decimal('0.29'))
        item_id = self.store.save_product(self.admin, product, [])
        try:
            found = self.store.products('ноутбук', low=Decimal('0.29'), high=Decimal('0.29'))
            self.assertIn(item_id, [r['id'] for r in found])
            self.assertEqual(next(r['price'] for r in found if r['id'] == item_id), Decimal('0.29'))
            self.assertNotIn(item_id, [r['id'] for r in self.store.products('НОУТБУК', low=Decimal('0.291'))])
            with self.assertRaises(ValueError):
                self.store.save_product(self.admin, dict(product, price=Decimal('0.291')), [])
        finally:
            self.store.delete_product(self.admin, item_id)

    def test_foreign_keys_and_restrict(self):
        with self.store.connect() as conn:
            self.assertEqual(conn.execute('PRAGMA foreign_keys').fetchone()[0], 1)
            self.assertEqual(conn.execute('PRAGMA foreign_key_check').fetchall(), [])
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.save_product(self.admin, dict(self.product, category_id=-1), [])
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.connect() as conn:
                conn.execute('DELETE FROM categories WHERE id=1')

    def test_restart_does_not_restore_deleted_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'isolated.sqlite3'
            store = Store(path)
            self.assertEqual(len(store.products()), 6)
            store.create_first_admin('first_admin', 'password123', 'Первый администратор')
            admin = store.authenticate('first_admin', 'password123')
            with self.assertRaises(ValueError):
                store.create_first_admin('other_admin', 'password123', 'Второй')
            store.delete_product(admin['id'], 1)
            restarted = Store(path)
            self.assertEqual(len(restarted.products()), 5)
            self.assertEqual(restarted.authenticate('first_admin', 'password123')['role'], 'admin')
            self.assertTrue(restarted.has_users())
