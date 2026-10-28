import tempfile
import unittest
from pathlib import Path
from webapp import create_app


class VerticalViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(Path(self.temp.name) / 'shop.sqlite3',
                              {'TESTING': True, 'SECRET_KEY': 'test-layout-only'})
        self.store = self.app.extensions['store']
        self.store.create_first_admin('admin', 'password123', 'Администратор')
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def login(self, view='vertical'):
        self.client.get('/login?view=' + view)
        with self.client.session_transaction() as state:
            csrf = state['csrf']
        return self.client.post('/login', data=dict(username='admin', password='password123', csrf=csrf), follow_redirects=True)

    def test_vertical_catalog_and_collapsed_filters(self):
        page = self.login().get_data(as_text=True)
        self.assertIn('class="layout-vertical"', page)
        self.assertIn('/static/vertical.css', page)
        self.assertIn('<details class="filter-disclosure">', page)
        self.assertIn('name="view" value="vertical"', page)
        self.assertEqual(page.count('<article class="product-card">'), 6)

    def test_layout_persists_through_pages_and_logout(self):
        self.login()
        for path in ('/products/1', '/settings', '/products/new', '/products/1/edit'):
            page = self.client.get(path)
            self.assertEqual(page.status_code, 200)
            self.assertIn('class="layout-vertical"', page.get_data(as_text=True))
        with self.client.session_transaction() as state:
            csrf = state['csrf']
        page = self.client.post('/logout', data={'csrf': csrf}, follow_redirects=True)
        self.assertIn('class="layout-vertical"', page.get_data(as_text=True))
        with self.client.session_transaction() as state:
            self.assertNotIn('user_id', state)

    def test_switch_to_grid_and_preserve_filters_in_links(self):
        self.login()
        page = self.client.get('/?view=vertical&q=Samsung&available=1').get_data(as_text=True)
        self.assertEqual(page.count('<article class="product-card">'), 1)
        self.assertIn('view=grid&amp;q=Samsung&amp;available=1', page)
        page = self.client.get('/?view=grid').get_data(as_text=True)
        self.assertIn('class="layout-grid"', page)
        self.assertNotIn('/static/vertical.css', page)
        self.assertNotIn('filter-disclosure', page)

    def test_unknown_mode_is_ignored(self):
        self.login()
        page = self.client.get('/?view=unknown').get_data(as_text=True)
        self.assertIn('class="layout-vertical"', page)
        with self.client.session_transaction() as state:
            self.assertEqual(state['layout'], 'vertical')

    def test_first_setup_keeps_vertical_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            app = create_app(Path(folder) / 'new.sqlite3', {'TESTING': True, 'SECRET_KEY': 'layout-setup'})
            client = app.test_client()
            page = client.get('/?view=vertical', follow_redirects=True)
            self.assertIn('class="layout-vertical"', page.get_data(as_text=True))
            with client.session_transaction() as state:
                csrf = state['csrf']
            page = client.post('/setup', data=dict(csrf=csrf, username='owner', password='password123',
                               repeat='password123', full_name='Администратор'), follow_redirects=True)
            self.assertEqual(page.status_code, 200)
            self.assertIn('class="layout-vertical"', page.get_data(as_text=True))
