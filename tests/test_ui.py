"""Offscreen smoke test with a deterministic stand-in; no PostgreSQL required."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from decimal import Decimal
from PySide6.QtWidgets import QApplication, QDialog
from app import Catalog, ProductEditor


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
