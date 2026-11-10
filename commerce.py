"""Shopping cart, checkout and order history for the web shop."""
from decimal import Decimal

def register_commerce(app, store, login_required, product_by_id):
    from flask import abort, flash, g, redirect, render_template, request, session, url_for
    with store.connect() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS orders(
          id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL REFERENCES users(id),
          customer_name TEXT NOT NULL,phone TEXT NOT NULL,address TEXT NOT NULL,comment TEXT NOT NULL DEFAULT '',
          total_cents INTEGER NOT NULL,payment_method TEXT NOT NULL,status TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        c.execute("""CREATE TABLE IF NOT EXISTS order_items(
          id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
          product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,product_name TEXT NOT NULL,
          unit_price_cents INTEGER NOT NULL,quantity INTEGER NOT NULL CHECK(quantity>0))""")
    def rows():
        out=[]; total=0; count=0
        for raw,qty in session.get('cart',{}).items():
            try: pid=int(raw); qty=int(qty)
            except (ValueError,TypeError): continue
            if not 1<=qty<=99: continue
            with store.connect() as c:
                p=c.execute("""SELECT p.id,p.name,p.price_cents,p.stock,p.category_id,c.name category,b.name brand
                  FROM products p JOIN categories c ON c.id=p.category_id JOIN brands b ON b.id=p.brand_id WHERE p.id=?""",(pid,)).fetchone()
            if not p or p['stock']<1: continue
            x=dict(p); x['quantity']=min(qty,x['stock']); x['price']=Decimal(x['price_cents'])/100
            x['line_total']=Decimal(x['price_cents']*x['quantity'])/100
            out.append(x); total+=x['price_cents']*x['quantity']; count+=x['quantity']
        return out,total,count
    @app.context_processor
    def cart_badge(): return {'cart_count':rows()[2]}
    @app.route('/cart',methods=['GET','POST'])
    @login_required
    def cart():
        cart=dict(session.get('cart',{}))
        if request.method=='POST':
            try: pid=int(request.form.get('product_id','')); qty=int(request.form.get('quantity','1'))
            except ValueError: flash('Неверное количество.','error'); return redirect(url_for('cart'))
            action=request.form.get('action','add')
            if action=='remove': cart.pop(str(pid),None)
            else:
                p=product_by_id(pid); n=qty if action=='update' else int(cart.get(str(pid),0))+qty
                if not 1<=n<=99 or n>p['stock']: flash('Недостаточно товара на складе.','error')
                else: cart[str(pid)]=n; flash('Корзина обновлена.','success')
            session['cart']=cart
            back=request.referrer or url_for('cart')
            return redirect(back if back.startswith('/') and not back.startswith('//') else url_for('cart'))
        items,total,count=rows()
        return render_template('commerce.html',mode='cart',items=items,total=Decimal(total)/100,count=count)
    @app.route('/checkout',methods=['GET','POST'])
    @login_required
    def checkout():
        items,total,count=rows()
        if not items: flash('Корзина пуста.','error'); return redirect(url_for('catalog'))
        if request.method=='POST':
            name=request.form.get('customer_name','').strip(); phone=request.form.get('phone','').strip()
            address=request.form.get('address','').strip(); comment=request.form.get('comment','').strip()
            method=request.form.get('payment_method','card')
            if not name or len(name)>150 or not phone or len(phone)>40 or not address or len(address)>300 or len(comment)>1000 or method not in ('card','cash'):
                flash('Проверьте контактные данные.','error'); return redirect(url_for('checkout'))
            with store.connect() as c:
                c.execute('BEGIN IMMEDIATE'); total_now=0; checked=[]
                for x in items:
                    p=c.execute('SELECT id,name,price_cents,stock FROM products WHERE id=?',(x['id'],)).fetchone()
                    if not p or p['stock']<x['quantity']: flash('Остаток изменился, проверьте корзину.','error'); return redirect(url_for('cart'))
                    total_now+=p['price_cents']*x['quantity']; checked.append((dict(p),x['quantity']))
                status='awaiting_payment' if method=='card' else 'awaiting_fulfillment'
                oid=c.execute("""INSERT INTO orders(user_id,customer_name,phone,address,comment,total_cents,payment_method,status)
                 VALUES(?,?,?,?,?,?,?,?)""",(g.user['id'],name,phone,address,comment,total_now,method,status)).lastrowid
                for p,q in checked:
                    c.execute("INSERT INTO order_items(order_id,product_id,product_name,unit_price_cents,quantity) VALUES(?,?,?,?,?)",(oid,p['id'],p['name'],p['price_cents'],q))
                    c.execute('UPDATE products SET stock=stock-? WHERE id=?',(q,p['id']))
            session['cart']={}
            return redirect(url_for('payment_order',order_id=oid) if method=='card' else url_for('order_detail',order_id=oid))
        return render_template('commerce.html',mode='checkout',items=items,total=Decimal(total)/100)
    @app.get('/payment/<int:order_id>')
    @login_required
    def payment_order(order_id):
        with store.connect() as c:
            o=c.execute("SELECT * FROM orders WHERE id=? AND user_id=? AND payment_method='card'",(order_id,g.user['id'])).fetchone()
            lines=c.execute('SELECT * FROM order_items WHERE order_id=?',(order_id,)).fetchall()
        if not o: abort(404)
        o=dict(o); o['total']=Decimal(o['total_cents'])/100
        return render_template('payment.html',order=o,lines=[dict(x) for x in lines])
    @app.get('/orders')
    @login_required
    def orders():
        with store.connect() as c: data=[dict(x) for x in c.execute('SELECT * FROM orders WHERE user_id=? ORDER BY id DESC',(g.user['id'],))]
        for x in data: x['total']=Decimal(x['total_cents'])/100
        return render_template('commerce.html',mode='orders',orders=data)
    @app.get('/orders/<int:order_id>')
    @login_required
    def order_detail(order_id):
        with store.connect() as c:
            o=c.execute('SELECT * FROM orders WHERE id=? AND user_id=?',(order_id,g.user['id'])).fetchone()
            lines=[dict(x) for x in c.execute('SELECT * FROM order_items WHERE order_id=?',(order_id,))]
        if not o: abort(404)
        o=dict(o); o['total']=Decimal(o['total_cents'])/100
        return render_template('commerce.html',mode='detail',order=o,items=lines)
