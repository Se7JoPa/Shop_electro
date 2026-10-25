"""Local browser edition. Author: Учебный проект."""
import hmac
import os
import secrets
import sqlite3
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.exceptions import SecurityError
from db import Store


def persistent_secret(path):
    """Keep login signatures valid after restart; never package the secret."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        value = path.read_text(encoding='ascii').strip()
        if len(value) < 64:
            raise ValueError('Файл ключа повреждён. Закройте программу и удалите только web_secret.key.')
        return value
    with os.fdopen(fd, 'w', encoding='ascii') as stream:
        value = secrets.token_hex(32)
        stream.write(value)
    return value


def create_app(database_path=None, test_config=None):
    app = Flask(__name__)
    store = Store(database_path)
    app.config.update(
        SESSION_COOKIE_NAME='electronics_shop_session', SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax', PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
        MAX_CONTENT_LENGTH=256 * 1024, TRUSTED_HOSTS=['127.0.0.1', 'localhost', '[::1]'],
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = persistent_secret(store.path.parent / 'web_secret.key')
    app.extensions['store'] = store

    def csrf_token():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    @app.before_request
    def load_user_and_csrf():
        g.user = None
        user_id = session.get('user_id')
        if isinstance(user_id, int):
            with store.connect() as conn:
                row = conn.execute('SELECT id,username,full_name,role,accent_color FROM users WHERE id=?', (user_id,)).fetchone()
                g.user = dict(row) if row else None
        if request.method == 'POST':
            expected = session.get('csrf')
            supplied = request.form.get('csrf', '')
            if not expected or not hmac.compare_digest(expected.encode('utf-8'), supplied.encode('utf-8')):
                abort(400, 'Форма устарела. Обновите страницу и повторите действие.')

    @app.after_request
    def response_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.endpoint != 'static':
            response.headers['Cache-Control'] = 'no-store'
        return response

    def login_required(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if not g.user:
                return redirect(url_for('login'))
            return func(*args, **kwargs)
        return wrapped

    def admin_required(func):
        @wraps(func)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user['role'] != 'admin':
                abort(403, 'Управление товарами доступно только администратору.')
            return func(*args, **kwargs)
        return wrapped

    def product_by_id(product_id):
        with store.connect() as conn:
            row = conn.execute('''SELECT p.*,c.name category,b.name brand FROM products p
                JOIN categories c ON c.id=p.category_id JOIN brands b ON b.id=p.brand_id
                WHERE p.id=?''', (product_id,)).fetchone()
        if row is None:
            abort(404, 'Товар не найден. Возможно, он уже удалён.')
        product = dict(row)
        product['price'] = Decimal(product['price_cents']) / 100
        return product

    @app.template_filter('money')
    def money(value):
        return f'{value:,.2f}'.replace(',', ' ').replace('.', ',')

    @app.context_processor
    def shared_context():
        accent = g.user['accent_color'] if g.get('user') else '#2563eb'
        rgb = [int(accent[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb]
        luminance = sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
        return dict(csrf_token=csrf_token, accent=accent,
                    accent_text='#111827' if luminance > .179 else '#ffffff')

    @app.route('/setup', methods=['GET', 'POST'])
    def setup():
        if store.has_users():
            return redirect(url_for('login'))
        error = None
        if request.method == 'POST':
            try:
                if request.form.get('password') != request.form.get('repeat'):
                    raise ValueError('Пароли не совпадают.')
                store.create_first_admin(request.form.get('username', ''), request.form.get('password', ''), request.form.get('full_name', ''))
                session.clear()
                flash('Администратор создан. Войдите с указанными данными.', 'success')
                return redirect(url_for('login'))
            except ValueError as exc:
                error = str(exc)
        return render_template('auth.html', mode='setup', error=error), 400 if error else 200

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if not store.has_users():
            return redirect(url_for('setup'))
        if g.user:
            return redirect(url_for('catalog'))
        error = None
        if request.method == 'POST':
            user = store.authenticate(request.form.get('username', ''), request.form.get('password', ''))
            if user:
                session.clear()
                session['user_id'] = user['id']
                session.permanent = True
                return redirect(url_for('catalog'))
            error = 'Неверный логин или пароль.'
        return render_template('auth.html', mode='login', error=error), 400 if error else 200

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if not store.has_users():
            return redirect(url_for('setup'))
        if g.user:
            return redirect(url_for('catalog'))
        error = None
        if request.method == 'POST':
            try:
                if request.form.get('password') != request.form.get('repeat'):
                    raise ValueError('Пароли не совпадают.')
                store.register(request.form.get('username', ''), request.form.get('password', ''), request.form.get('full_name', ''))
                session.clear()
                flash('Аккаунт создан. Теперь можно войти.', 'success')
                return redirect(url_for('login'))
            except ValueError as exc:
                error = str(exc)
            except sqlite3.IntegrityError:
                error = 'Этот логин уже занят. Выберите другой.'
        return render_template('auth.html', mode='register', error=error), 400 if error else 200

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.get('/')
    @login_required
    def catalog():
        error = None
        filters = {key: request.args.get(key, '') for key in ('q', 'category', 'brand', 'low', 'high', 'available', 'sort')}
        rows = []
        try:
            def price(raw, default):
                if not raw.strip():
                    return default
                value = Decimal(raw.replace(',', '.'))
                if not value.is_finite() or not 0 <= value <= Decimal('9999999999.99'):
                    raise ValueError('Укажите допустимую цену.')
                return value
            low, high = price(filters['low'], Decimal(0)), price(filters['high'], None)
            if high is not None and low > high:
                raise ValueError('Цена «до» должна быть не меньше цены «от».')
            category = int(filters['category']) if filters['category'] else None
            brand = int(filters['brand']) if filters['brand'] else None
            rows = store.products(filters['q'][:200], category, brand, low, high, filters['available'] == '1')
            if filters['sort'] == 'price_asc':
                rows.sort(key=lambda p: (p['price'], p['id']))
            elif filters['sort'] == 'price_desc':
                rows.sort(key=lambda p: (-p['price'], p['id']))
        except (ValueError, InvalidOperation):
            error = 'Проверьте фильтры: цены должны быть числами, цена «до» не меньше цены «от».'
        return render_template('catalog.html', products=rows, filters=filters,
            categories=store.references('categories'), brands=store.references('brands'), error=error), 400 if error else 200

    @app.get('/products/<int:product_id>')
    @login_required
    def detail(product_id):
        return render_template('detail.html', product=product_by_id(product_id), specs=store.specs(product_id))

    @app.route('/products/new', methods=['GET', 'POST'])
    @admin_required
    def new_product():
        return edit_form(None)

    @app.route('/products/<int:product_id>/edit', methods=['GET', 'POST'])
    @admin_required
    def edit_product(product_id):
        return edit_form(product_by_id(product_id))

    def edit_form(product):
        error = None
        values = dict(product) if product else {}
        values['specs'] = '\n'.join(f"{r['name']}: {r['value']}" for r in store.specs(product['id'])) if product else ''
        if request.method == 'POST':
            values = request.form.to_dict()
            try:
                price = Decimal(values.get('price', '').replace(',', '.'))
                specs = []
                for line in values.get('specs', '').splitlines():
                    if not line.strip():
                        continue
                    name, separator, value = line.partition(':')
                    if not separator or not name.strip() or not value.strip():
                        raise ValueError('Характеристики: одна на строку, в формате «Название: значение».')
                    if len(name.strip()) > 100 or len(value.strip()) > 500:
                        raise ValueError('Характеристика слишком длинная: название до 100, значение до 500 символов.')
                    specs.append((name.strip(), value.strip()))
                data = dict(name=values.get('name', ''), description=values.get('description', ''), price=price,
                            stock=int(values.get('stock', '')), category_id=int(values.get('category_id', '')),
                            brand_id=int(values.get('brand_id', '')))
                item_id = store.save_product(g.user['id'], data, specs, product['id'] if product else None)
                flash('Товар сохранён.', 'success')
                return redirect(url_for('detail', product_id=item_id))
            except (ValueError, InvalidOperation) as exc:
                error = str(exc) if isinstance(exc, ValueError) else 'Укажите корректную цену.'
            except sqlite3.IntegrityError:
                error = 'Проверьте категорию, бренд и характеристики товара.'
        return render_template('editor.html', product=product, values=values, error=error,
            categories=store.references('categories'), brands=store.references('brands')), 400 if error else 200

    @app.route('/products/<int:product_id>/delete', methods=['GET', 'POST'])
    @admin_required
    def delete_product(product_id):
        product = product_by_id(product_id)
        if request.method == 'POST':
            store.delete_product(g.user['id'], product_id)
            flash('Товар удалён.', 'success')
            return redirect(url_for('catalog'))
        return render_template('delete.html', product=product)

    @app.route('/settings', methods=['GET', 'POST'])
    @login_required
    def settings():
        error = None
        if request.method == 'POST':
            try:
                store.set_color(g.user['id'], request.form.get('color', ''))
                flash('Цвет интерфейса сохранён.', 'success')
                return redirect(url_for('settings'))
            except ValueError as exc:
                error = str(exc)
        return render_template('settings.html', error=error), 400 if error else 200

    @app.errorhandler(sqlite3.Error)
    def database_error(exc):
        app.logger.exception('Database error')
        return render_template('error.html', code=503,
            message='База данных временно недоступна. Закройте её в другом редакторе и повторите действие.'), 503

    for status in (400, 403, 404, 405, 413):
        def handler(error):
            if isinstance(error, SecurityError):
                return 'Недопустимый адрес сервера.', 400, {'Content-Type': 'text/plain; charset=utf-8'}
            return render_template('error.html', code=error.code, message=error.description), error.code
        app.register_error_handler(status, handler)
    return app
