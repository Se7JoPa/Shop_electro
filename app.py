"""Desktop electronics catalogue. Author: Учебный проект."""
import sys
from decimal import Decimal
import sqlite3
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication, QWidget, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QDoubleSpinBox, QSpinBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTextEdit, QDialogButtonBox, QColorDialog, QAbstractItemView,
)
from db import Store


def error_message(parent, error):
    if isinstance(error, sqlite3.IntegrityError):
        text = 'Нарушено ограничение базы данных. Проверьте логин, характеристики и связанные записи.'
    elif isinstance(error, sqlite3.Error):
        text = 'Ошибка SQLite. Проверьте доступ к папке data и файлу базы. Если база открыта другой программой, закройте её и повторите.'
    else:
        text = str(error)
    QMessageBox.warning(parent, 'Не удалось выполнить действие', text)


def guarded(method):
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except (sqlite3.Error, ValueError, PermissionError, OSError) as error:
            error_message(self, error)
    return wrapper


def apply_style(app, color='#2563eb'):
    # Use dark button text for light accents so arbitrary user colors stay readable.
    c = QColor(color)
    fg = '#0f172a' if c.lightnessF() > 0.6 else '#ffffff'
    app.setStyleSheet('''
        QWidget {font-family: "Segoe UI", "Arial"; font-size: 14px; color: #172033;}
        QDialog, QWidget#main {background: #f3f6fb;}
        QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background: white; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px;}
        QPushButton {background: ACCENT; color: FOREGROUND; padding: 9px 16px;
            border: 0; border-radius: 6px; font-weight: 600;}
        QPushButton:disabled {background: #cbd5e1; color: #64748b;}
        QTableWidget {background: white; border: 1px solid #d9e2ef; gridline-color: #e2e8f0;}
        QTableWidget::item:selected {background: ACCENT; color: FOREGROUND;}
        QHeaderView::section {background: #e7edf6; padding: 9px; border: 0; font-weight: 600;}
        QLabel#title {font-size: 26px; font-weight: 700; color: #0f172a;}
    '''.replace('ACCENT', color).replace('FOREGROUND', fg))


class Registration(QDialog):
    def __init__(self, store, parent=None, first_admin=False):
        super().__init__(parent)
        self.store = store
        self.first_admin = first_admin
        self.setWindowTitle('Первый запуск | Создание администратора' if first_admin else 'Регистрация покупателя')
        self.setMinimumWidth(400)
        form = QFormLayout(self)
        self.name, self.login, self.password, self.repeat = [QLineEdit() for _ in range(4)]
        for edit in (self.password, self.repeat):
            edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow('Имя', self.name)
        form.addRow('Логин', self.login)
        form.addRow('Пароль', self.password)
        form.addRow('Повтор пароля', self.repeat)
        submit = QPushButton('Создать аккаунт')
        submit.clicked.connect(self.submit)
        form.addRow(submit)

    @guarded
    def submit(self):
        if self.password.text() != self.repeat.text():
            raise ValueError('Пароли не совпадают.')
        method = self.store.create_first_admin if self.first_admin else self.store.register
        method(self.login.text(), self.password.text(), self.name.text())
        QMessageBox.information(self, 'Готово', 'Аккаунт создан. Теперь можно войти.')
        self.accept()


class Login(QDialog):
    def __init__(self, store):
        super().__init__()
        self.store, self.user = store, None
        self.setWindowTitle('Электроника | Вход')
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        title = QLabel('Магазин электроники')
        title.setObjectName('title')
        layout.addWidget(title)
        layout.addWidget(QLabel('Войдите для просмотра каталога'))
        self.login, self.password = QLineEdit(), QLineEdit()
        self.login.setPlaceholderText('Логин')
        self.password.setPlaceholderText('Пароль')
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.login)
        layout.addWidget(self.password)
        enter, register = QPushButton('Войти'), QPushButton('Регистрация покупателя')
        enter.clicked.connect(self.submit)
        self.password.returnPressed.connect(self.submit)
        register.clicked.connect(lambda: Registration(store, self).exec())
        layout.addWidget(enter)
        layout.addWidget(register)

    @guarded
    def submit(self):
        user = self.store.authenticate(self.login.text(), self.password.text())
        if user is None:
            raise ValueError('Неверный логин или пароль.')
        self.user = user
        self.accept()


class ProductEditor(QDialog):
    def __init__(self, store, user, parent, product=None):
        super().__init__(parent)
        self.store, self.user, self.product = store, user, product
        self.setWindowTitle('Редактирование товара' if product else 'Добавление товара')
        self.resize(570, 590)
        form = QFormLayout(self)
        self.name, self.description = QLineEdit(), QTextEdit()
        self.description.setMaximumHeight(95)
        self.price, self.stock = QDoubleSpinBox(), QSpinBox()
        self.price.setRange(0, 9999999999.99)
        self.price.setDecimals(2)
        self.price.setSuffix(' руб.')
        self.stock.setRange(0, 2147483647)
        self.category, self.brand = QComboBox(), QComboBox()
        for combo, kind in [(self.category, 'categories'), (self.brand, 'brands')]:
            for row in store.references(kind):
                combo.addItem(row['name'], row['id'])
        self.specs = QTextEdit()
        self.specs.setPlaceholderText('Одна характеристика на строку:\nПамять: 128 ГБ\nЦвет: чёрный')
        for label, widget in [('Название', self.name), ('Описание', self.description),
                              ('Цена', self.price), ('Остаток', self.stock),
                              ('Категория', self.category), ('Бренд', self.brand),
                              ('Характеристики', self.specs)]:
            form.addRow(label, widget)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText('Сохранить')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Отмена')
        buttons.accepted.connect(self.submit)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)
        if product:
            self.name.setText(product['name'])
            self.description.setPlainText(product['description'])
            self.price.setValue(float(product['price']))
            self.stock.setValue(product['stock'])
            self.category.setCurrentIndex(self.category.findData(product['category_id']))
            self.brand.setCurrentIndex(self.brand.findData(product['brand_id']))
            self.specs.setPlainText('\n'.join(f"{s['name']}: {s['value']}" for s in store.specs(product['id'])))

    @guarded
    def submit(self):
        specs = []
        for line in self.specs.toPlainText().splitlines():
            if not line.strip():
                continue
            name, separator, value = line.partition(':')
            if not separator or not name.strip() or not value.strip():
                raise ValueError('Характеристики задаются в формате «Название: значение».')
            if len(name.strip()) > 100 or len(value.strip()) > 500:
                raise ValueError('Название характеристики: до 100 символов, значение: до 500.')
            specs.append((name.strip(), value.strip()))
        name = self.name.text().strip()
        if len(name) > 200:
            raise ValueError('Название товара: до 200 символов.')
        if self.category.currentData() is None or self.brand.currentData() is None:
            raise ValueError('Выберите категорию и бренд.')
        data = dict(name=name, description=self.description.toPlainText(),
                    price=Decimal(str(self.price.value())), stock=self.stock.value(),
                    category_id=self.category.currentData(), brand_id=self.brand.currentData())
        self.store.save_product(self.user['id'], data, specs,
                                self.product['id'] if self.product else None)
        self.accept()


class Catalog(QWidget):
    def __init__(self, store, user):
        super().__init__()
        self.store, self.user, self.rows = store, user, []
        self.setObjectName('main')
        self.setWindowTitle('Магазин электроники | Учебный проект')
        self.resize(1150, 720)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        header = QHBoxLayout()
        title = QLabel('Магазин электроники')
        title.setObjectName('title')
        header.addWidget(title)
        header.addStretch()
        role = 'Администратор' if user['role'] == 'admin' else 'Покупатель'
        header.addWidget(QLabel(f"{user['full_name']} · {role}"))
        color, logout = QPushButton('Цвет интерфейса'), QPushButton('Выйти')
        color.clicked.connect(self.choose_color)
        logout.clicked.connect(self.close)
        header.addWidget(color)
        header.addWidget(logout)
        layout.addLayout(header)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Поиск по названию товара...')
        layout.addWidget(self.search)
        filters = QHBoxLayout()
        self.category, self.brand = QComboBox(), QComboBox()
        self.category.addItem('Все категории', None)
        self.brand.addItem('Все бренды', None)
        for combo, kind in [(self.category, 'categories'), (self.brand, 'brands')]:
            for row in store.references(kind):
                combo.addItem(row['name'], row['id'])
        self.low, self.high = QDoubleSpinBox(), QDoubleSpinBox()
        for spin in (self.low, self.high):
            spin.setRange(0, 9999999999.99)
            spin.setSuffix(' руб.')
        self.high.setSpecialValueText('Без верхнего предела')
        self.available = QCheckBox('В наличии')
        for widget in (self.category, self.brand, QLabel('От'), self.low, QLabel('До'), self.high, self.available):
            filters.addWidget(widget)
        reset = QPushButton('Сбросить')
        reset.clicked.connect(self.reset)
        filters.addWidget(reset)
        layout.addLayout(filters)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['Название', 'Категория', 'Бренд', 'Цена, руб.', 'Остаток'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 5):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(lambda _: self.details())
        layout.addWidget(self.table)
        footer = QHBoxLayout()
        self.count = QLabel()
        footer.addWidget(self.count)
        footer.addStretch()
        self.add_button = None
        actions = [('Подробнее', self.details), ('Обновить', self.refresh)]
        if user['role'] == 'admin':
            actions += [('Добавить', self.add), ('Редактировать', self.edit), ('Удалить', self.delete)]
        for label, callback in actions:
            button = QPushButton(label)
            button.clicked.connect(callback)
            footer.addWidget(button)
            if label == 'Добавить':
                self.add_button = button
        layout.addLayout(footer)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.refresh)
        self.search.textChanged.connect(lambda: self.timer.start(350))
        for combo in (self.category, self.brand):
            combo.currentIndexChanged.connect(lambda: self.timer.start(150))
        for spin in (self.low, self.high):
            spin.valueChanged.connect(lambda: self.timer.start(350))
        self.available.toggled.connect(lambda: self.timer.start(150))
        apply_style(QApplication.instance(), user['accent_color'])
        self.refresh()

    @guarded
    def refresh(self):
        high = self.high.value() or None
        if high is not None and high < self.low.value():
            raise ValueError('Верхняя цена должна быть не меньше нижней.')
        self.rows = self.store.products(self.search.text(), self.category.currentData(),
            self.brand.currentData(), self.low.value(), high, self.available.isChecked())
        self.table.setRowCount(len(self.rows))
        for i, row in enumerate(self.rows):
            values = [row['name'], row['category'], row['brand'],
                      f"{row['price']:,.2f}".replace(',', ' '), str(row['stock'])]
            for j, value in enumerate(values):
                self.table.setItem(i, j, QTableWidgetItem(value))
        self.count.setText(f'Найдено товаров: {len(self.rows)}' if self.rows else 'Товары не найдены. Измените условия поиска.')

    def reset(self):
        self.search.clear()
        self.category.setCurrentIndex(0)
        self.brand.setCurrentIndex(0)
        self.low.setValue(0)
        self.high.setValue(0)
        self.available.setChecked(False)
        self.timer.stop()
        self.refresh()

    def selected(self):
        i = self.table.currentRow()
        if i < 0 or i >= len(self.rows):
            raise ValueError('Сначала выберите товар в таблице.')
        return self.rows[i]

    @guarded
    def details(self):
        row = self.selected()
        dialog = QDialog(self)
        dialog.setWindowTitle('Карточка товара')
        dialog.resize(540, 440)
        layout = QVBoxLayout(dialog)
        body = QTextEdit()
        body.setReadOnly(True)
        specs = '\n'.join(f"{s['name']}: {s['value']}" for s in self.store.specs(row['id']))
        body.setPlainText(f"{row['name']}\n\nКатегория: {row['category']}\nБренд: {row['brand']}\n"
                          f"Цена: {row['price']:.2f} руб.\nОстаток: {row['stock']}\n\n"
                          f"{row['description']}\n\nХарактеристики:\n{specs or 'Не указаны'}")
        layout.addWidget(body)
        close = QPushButton('Закрыть')
        close.clicked.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    @guarded
    def add(self):
        if ProductEditor(self.store, self.user, self).exec():
            self.refresh()

    @guarded
    def edit(self):
        if ProductEditor(self.store, self.user, self, self.selected()).exec():
            self.refresh()

    @guarded
    def delete(self):
        row = self.selected()
        answer = QMessageBox.question(self, 'Удаление товара', f"Удалить «{row['name']}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.store.delete_product(self.user['id'], row['id'])
            self.refresh()

    @guarded
    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.user['accent_color']), self, 'Цвет интерфейса')
        if color.isValid():
            self.store.set_color(self.user['id'], color.name())
            self.user['accent_color'] = color.name()
            apply_style(QApplication.instance(), color.name())


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('ElectronicsShop')
    app.setStyle('Fusion')
    apply_style(app)
    # Main loop also supports logging out and signing in with another account.
    app.setQuitOnLastWindowClosed(False)
    try:
        store = Store()
        if not store.has_users():
            setup = Registration(store, first_admin=True)
            if setup.exec() != QDialog.DialogCode.Accepted:
                return 0
    except (sqlite3.Error, OSError, ValueError) as error:
        error_message(None, error)
        return 1
    while True:
        apply_style(app)
        login = Login(store)
        if login.exec() != QDialog.DialogCode.Accepted:
            break
        try:
            window = Catalog(store, login.user)
        except (sqlite3.Error, ValueError) as error:
            error_message(login, error)
            continue
        window.show()
        # Explicit quit only ends this application event loop, allowing a new login.
        window.destroyed.connect(app.quit)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        app.exec()
    return 0


if __name__ == '__main__':
    sys.exit(main())
