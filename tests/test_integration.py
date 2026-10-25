"""Runs only on a PostgreSQL database with name ending in _test."""
import os
import unittest
from decimal import Decimal
from uuid import uuid4
from db import Store
from security import hash_password
import psycopg


@unittest.skipUnless(os.getenv('DB_NAME', '').endswith('_test'), 'Set DB_NAME to a disposable *_test database')
class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = Store()
        cls.tag = 'test_' + uuid4().hex[:12]
        with cls.store.connect() as conn:
            cls.admin = conn.execute('''INSERT INTO users(username,password_hash,full_name,role)
                VALUES (%s,%s,%s,'admin') RETURNING id''',
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
            conn.execute('DELETE FROM products WHERE name LIKE %s', (cls.tag + '%',))
            conn.execute('DELETE FROM users WHERE id IN (%s,%s)', (cls.admin, cls.customer))

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
            with self.assertRaises(psycopg.errors.CheckViolation):
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
