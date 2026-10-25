"""Rebuild ER_diagram.pdf: pip install reportlab, then python docs/build_diagram.py."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

ROOT = Path(__file__).resolve().parent
font_path = os.getenv('ER_FONT_PATH', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
if not Path(font_path).is_file():
    raise SystemExit('Укажите ER_FONT_PATH: путь к TTF-шрифту с поддержкой русского языка.')
pdfmetrics.registerFont(TTFont('ER', font_path))
c = canvas.Canvas(str(ROOT / 'ER_diagram.pdf'), pagesize=landscape(A4))
c.setTitle('Магазин электроники - ER-диаграмма')
c.setAuthor('Магазин электроники')


def text(x, y, value, size=9, color='#24344b'):
    c.setFillColor(color)
    c.setFont('ER', size)
    c.drawString(x, y, value)


def box(x, top, width, title, rows):
    height = 36 + 19 * len(rows)
    c.setFillColor('#f5f8fd')
    c.setStrokeColor('#bfd0e6')
    c.roundRect(x, top - height, width, height, 7, fill=1, stroke=1)
    c.setFillColor('#2157b5')
    c.roundRect(x, top - 30, width, 30, 7, fill=1, stroke=0)
    text(x + 12, top - 20, title, 11, '#ffffff')
    for i, row in enumerate(rows):
        text(x + 10, top - 47 - i * 19, row, 8)
    return height


def connection(points, label, label_x, label_y):
    c.setStrokeColor('#2157b5')
    c.setLineWidth(1.4)
    path = c.beginPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    c.drawPath(path)
    x, y = points[-1]
    c.line(x, y, x - 6, y + 4)
    c.line(x, y, x - 6, y - 4)
    text(label_x, label_y, label, 9, '#2157b5')


text(32, 551, 'Магазин электроники', 24, '#123364')
text(32, 527, 'ER-диаграмма · SQLite', 11)
box(32, 480, 214, 'categories | Категории', [
    'PK  id: INTEGER', 'UQ  name: varchar(100)'])
box(32, 327, 214, 'brands | Бренды', [
    'PK  id: INTEGER', 'UQ  name: varchar(100)'])
box(300, 480, 235, 'products | Товары', [
    'PK  id: INTEGER', 'name: varchar(200)', 'description: text',
    'price_cents: INTEGER >= 0', 'stock: integer >= 0',
    'FK  category_id: INTEGER', 'FK  brand_id: INTEGER', 'created_at: TEXT (UTC)'])
box(587, 480, 222, 'product_specs | Характеристики', [
    'PK  id: INTEGER', 'FK  product_id: INTEGER',
    'name: varchar(100)', 'value: varchar(500)', 'UQ  (product_id, name)'])
box(587, 313, 222, 'users | Пользователи', [
    'PK  id: INTEGER', 'UQ  username: varchar(50)',
    'password_hash: text', 'full_name: varchar(150)',
    "role: admin / customer", 'accent_color: varchar(7)', 'created_at: TEXT (UTC)'])
connection([(246, 435), (268, 435), (268, 338), (300, 338)], '1:N', 251, 447)
connection([(246, 282), (280, 282), (280, 319), (300, 319)], '1:N', 250, 268)
connection([(535, 414), (558, 414), (558, 414), (587, 414)], '1:N', 541, 426)
text(32, 225, 'Правила связей', 11, '#123364')
text(32, 203, 'Категория и бренд обязательны для каждого товара.', 9)
text(32, 185, 'Удаление используемой категории / бренда: RESTRICT.', 9)
text(32, 167, 'Удаление товара удаляет его характеристики: CASCADE.', 9)
text(32, 149, 'Цена хранится целым числом копеек, в окне показаны рубли.', 9)
text(32, 131, 'users: доступ и цвет. Связей с каталогом нет; заказов нет.', 9)
c.setStrokeColor('#d7e1ef')
c.line(32, 77, 809, 77)
text(32, 57, 'PK - первичный ключ    FK - внешний ключ    UQ - уникальность    1:N - один ко многим', 9)
text(32, 39, 'Все поля NOT NULL. FK включаются в каждом соединении. Схема: schema.sql.', 9)
c.showPage()
c.save()
