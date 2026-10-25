"""Offscreen smoke test with a deterministic stand-in; no user database required."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from decimal import Decimal
from PySide6.QtWidgets import QApplication, QDialog
from app import Catalog, ProductEditor, Registration, Login
from db import Store


class DemoStore:
    def __init__(self):
        self.saved = None
    def references(self, kind):
        return [{'id': 1, 'name': 'Смартфоны' if kind == 'categories' else 'Samsung'}]
    def products(self, *args):
        return [dict(id=1, name='Samsung Galaxy A55', description='Смартфон для учебного каталога.',
                     price=Decimal('34990.00'), stock=12, category_id=1, brand_id=1,
                     category='Смартфоны', brand='Samsung')]
    def specs(self, item_id):
        return [{'name': 'Память', 'value': '128 ГБ'}]
    def save_product(self, *args):
        self.saved = args


class InterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def user(self, role='admin'):
        return dict(id=1, full_name='Учебный проект', role=role, accent_color='#2563eb')

    def test_roles_and_catalog(self):
        for role in ('admin', 'customer'):
            window = Catalog(DemoStore(), self.user(role))
            window.show()
            self.app.processEvents()
            self.assertEqual(window.table.rowCount(), 1)
            self.assertEqual(window.add_button is not None, role == 'admin')
            if os.getenv('UI_SCREENSHOT') and role == 'admin':
                window.grab().save(os.environ['UI_SCREENSHOT'])
            window.close()

    def test_editor_submits_product_and_specs(self):
        store = DemoStore()
        editor = ProductEditor(store, self.user(), None)
        editor.name.setText('Новый товар')
        editor.price.setValue(1999.50)
        editor.stock.setValue(4)
        editor.specs.setPlainText('Память: 256 ГБ\nЦвет: Синий')
        editor.submit()
        self.assertEqual(editor.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(store.saved[1]['price'], Decimal('1999.5'))
        self.assertEqual(store.saved[2], [('Память', '256 ГБ'), ('Цвет', 'Синий')])

    def test_first_launch_login_and_editor_on_real_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / 'gui.sqlite3')
            setup = Registration(store, first_admin=True)
            setup.name.setText('Учебный проект')
            setup.login.setText('shop_admin')
            setup.password.setText('password123')
            setup.repeat.setText('password123')
            with patch('app.QMessageBox.information'):
                setup.submit()
            self.assertEqual(setup.result(), QDialog.DialogCode.Accepted)
            login = Login(store)
            login.login.setText('shop_admin')
            login.password.setText('password123')
            login.submit()
            self.assertEqual(login.result(), QDialog.DialogCode.Accepted)
            catalog = Catalog(store, login.user)
            self.assertEqual(catalog.table.rowCount(), 6)
            editor = ProductEditor(store, login.user, catalog)
            editor.name.setText('Тестовый планшет')
            editor.price.setValue(12345.67)
            editor.stock.setValue(2)
            editor.specs.setPlainText('Память: 128 ГБ')
            editor.submit()
            self.assertEqual(editor.result(), QDialog.DialogCode.Accepted)
            catalog.refresh()
            self.assertEqual(catalog.table.rowCount(), 7)
            self.assertEqual(store.products('ПЛАНШЕТ')[0]['price'], Decimal('12345.67'))
            if os.getenv('SQLITE_UI_SCREENSHOT'):
                catalog.show()
                self.app.processEvents()
                catalog.grab().save(os.environ['SQLITE_UI_SCREENSHOT'])
            catalog.close()
