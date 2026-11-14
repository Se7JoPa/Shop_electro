"""Bulk catalog repricing. Administrator-only preview and confirmation."""
from decimal import Decimal, InvalidOperation
from flask import abort, flash, g, redirect, render_template, request, url_for


def register_repricing(app, store, admin_required):
    def cents(raw):
        try:
            amount = Decimal(str(raw).strip().replace(',', '.'))
        except (InvalidOperation, ValueError):
            raise ValueError('Укажите корректные суммы.')
        if not amount.is_finite() or amount < 0 or amount > Decimal('9999999999.99') or amount * 100 != (amount * 100).to_integral_value():
            raise ValueError('Цена должна быть от 0 до 9 999 999 999,99 ₽, не более двух знаков после запятой.')
        return int(amount * 100)

    @app.route('/admin/repricing', methods=['GET', 'POST'])
    @admin_required
    def repricing():
        threshold = request.form.get('minimum', '')
        target = request.form.get('new_price', '')
        preview = []
        error = None
        if request.method == 'POST':
            try:
                minimum_cents = cents(threshold)
                target_cents = cents(target)
                with store.connect() as conn:
                    store.require_admin(conn, g.user['id'])
                    if request.form.get('action') == 'apply':
                        conn.execute('BEGIN IMMEDIATE')
                        result = conn.execute('UPDATE products SET price_cents=? WHERE price_cents > ? AND price_cents != ?',
                                              (target_cents, minimum_cents, target_cents))
                        flash(f'Цены обновлены. Изменено товаров: {result.rowcount}.', 'success')
                        return redirect(url_for('repricing'))
                    if request.form.get('action') != 'calculate':
                        abort(400)
                    preview = [dict(row) for row in conn.execute(
                        'SELECT id,name,price_cents FROM products WHERE price_cents > ? AND price_cents != ? ORDER BY name,id',
                        (minimum_cents, target_cents))]
            except ValueError as exc:
                error = str(exc)
        return render_template('repricing.html', minimum=threshold, new_price=target,
                               preview=preview, calculated=request.method == 'POST' and not error,
                               error=error), 400 if error else 200
