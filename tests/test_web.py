"""HTTP and permission checks with Flask's client and real isolated SQLite."""
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal
from webapp import create_app


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'shop.sqlite3'
        self.app = create_app(self.path, {'TESTING': True, 'SECRET_KEY': 'test-only-key'})
        self.store = self.app.extensions['store']
        self.store.create_first_admin('admin', 'password123', 'Учебный проект')
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def post(self, url, data=None, follow=False):
        self.client.get('/login', follow_redirects=True)
        with self.client.session_transaction() as state:
            csrf = state['csrf']
        return self.client.post(url, data={**(data or {}), 'csrf': csrf}, follow_redirects=follow)

    def login(self, username='admin', password='password123'):
        return self.post('/login', dict(username=username, password=password), True)

    def test_first_setup_and_no_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / 'new.sqlite3', {'TESTING': True, 'SECRET_KEY': 'test'})
            client = app.test_client()
            self.assertEqual(client.get('/login').location, '/setup')
            client.get('/setup')
            with client.session_transaction() as s:
                csrf = s['csrf']
            result = client.post('/setup', data=dict(csrf=csrf, username='first', password='password123',
                repeat='password123', full_name='Первый'), follow_redirects=True)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(app.extensions['store'].authenticate('first', 'password123')['role'], 'admin')
            self.assertEqual(client.get('/setup').location, '/login')

    def test_login_logout_and_no_password_hash_in_cookie(self):
        self.assertEqual(self.client.get('/').status_code, 302)
        self.assertEqual(self.login(password='wrong').status_code, 400)
        self.assertEqual(self.login().status_code, 200)
        with self.client.session_transaction() as state:
            self.assertIn('user_id', state)
            self.assertNotIn('password_hash', state)
        self.assertEqual(self.post('/logout').status_code, 302)
        self.assertEqual(self.client.get('/products/1').status_code, 302)

    def test_register_customer_and_duplicate_login(self):
        values = dict(username='buyer', password='password123', repeat='password123', full_name='Покупатель')
        self.assertEqual(self.post('/register', values, True).status_code, 200)
        self.assertEqual(self.store.authenticate('buyer', 'password123')['role'], 'customer')
        self.assertEqual(self.post('/register', values).status_code, 400)

    def test_customer_cannot_use_admin_routes(self):
        self.store.register('buyer', 'password123', 'Покупатель')
        page = self.login('buyer')
        self.assertNotIn('Добавить товар', page.get_data(as_text=True))
        for url in ('/products/new', '/products/1/edit', '/products/1/delete'):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(self.post(url).status_code, 403)
        self.assertEqual(len(self.store.products()), 6)

    def test_csrf_required_and_delete_requires_post(self):
        self.login()
        self.assertEqual(self.client.post('/products/1/delete').status_code, 400)
        self.assertEqual(self.client.post('/products/1/delete', data={'csrf': 'неверно'}).status_code, 400)
        self.assertEqual(self.client.get('/products/1/delete').status_code, 200)
        self.assertEqual(len(self.store.products()), 6)
        self.assertEqual(self.post('/products/1/delete').status_code, 302)
        self.assertEqual(len(self.store.products()), 5)
        self.assertEqual(self.store.specs(1), [])

    def test_create_edit_detail_and_validation(self):
        self.login()
        data = dict(name='Тестовый планшет', description='Описание', price='12345,67', stock='4',
                    category_id='1', brand_id='1', specs='Память: 128 ГБ\nЦвет: Синий')
        result = self.post('/products/new', data)
        self.assertEqual(result.status_code, 302)
        row = self.store.products('планшет')[0]
        self.assertEqual(row['price'], Decimal('12345.67'))
        self.assertEqual(len(self.store.specs(row['id'])), 2)
        result = self.post(f"/products/{row['id']}/edit", dict(data, price='9999.99'), True)
        self.assertEqual(result.status_code, 200)
        self.assertIn('9 999,99', result.get_data(as_text=True))
        self.assertEqual(self.post('/products/new', dict(data, price='-1')).status_code, 400)
        self.assertEqual(self.post('/products/new', dict(data, specs='Без двоеточия')).status_code, 400)
        self.assertEqual(self.post('/products/new', dict(data, category_id='9999')).status_code, 400)

    def test_filters_search_sort_empty_and_bad_input(self):
        self.login()
        result = self.client.get('/?q=Samsung&category=1&available=1&low=30000&high=40000')
        text = result.get_data(as_text=True)
        self.assertEqual(result.status_code, 200)
        self.assertIn('Samsung Galaxy A55', text)
        self.assertNotIn('Samsung Odyssey', text)
        self.assertIn('Ничего не нашлось', self.client.get('/?q=неизвестный').get_data(as_text=True))
        self.assertEqual(self.client.get('/?low=nan').status_code, 400)
        self.assertEqual(self.client.get('/?low=900&high=10').status_code, 400)
        text = self.client.get('/?sort=price_asc').get_data(as_text=True)
        self.assertLess(text.index('Samsung Odyssey G5'), text.index('ASUS TUF Gaming'))

    def test_color_persistence_and_html_escape(self):
        self.login()
        self.assertEqual(self.post('/settings', {'color': '#16a085'}, True).status_code, 200)
        self.assertEqual(self.store.authenticate('admin', 'password123')['accent_color'], '#16a085')
        self.assertIn('--accent:#16a085', self.client.get('/').get_data(as_text=True))
        self.assertEqual(self.post('/settings', {'color': 'red;display:none'}).status_code, 400)
        admin = self.store.authenticate('admin', 'password123')
        self.store.save_product(admin['id'], dict(name='<script>alert(1)</script>', description='<img onerror=bad>',
            price=Decimal('1'), stock=1, category_id=1, brand_id=1), [])
        text = self.client.get('/').get_data(as_text=True)
        self.assertNotIn('<script>alert(1)</script>', text)
        self.assertIn('&lt;script&gt;', text)

    def test_headers_missing_product_and_host_validation(self):
        self.login()
        result = self.client.get('/')
        self.assertEqual(result.headers['X-Frame-Options'], 'DENY')
        self.assertEqual(result.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.client.get('/products/9999').status_code, 404)
        self.assertEqual(self.client.get('/', headers={'Host': 'attacker.invalid'}).status_code, 400)

    def test_existing_desktop_database_is_reused(self):
        admin = self.store.authenticate('admin', 'password123')
        self.store.delete_product(admin['id'], 1)
        reopened = create_app(self.path, {'TESTING': True, 'SECRET_KEY': 'test'})
        store = reopened.extensions['store']
        self.assertEqual(len(store.products()), 5)
        self.assertIsNotNone(store.authenticate('admin', 'password123'))

    def test_session_secret_is_generated_once(self):
        first = create_app(self.path, {'TESTING': True})
        second = create_app(self.path, {'TESTING': True})
        self.assertEqual(first.secret_key, second.secret_key)
        self.assertEqual(len(first.secret_key), 64)
        self.assertTrue((self.path.parent / 'web_secret.key').is_file())
