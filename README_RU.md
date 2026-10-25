# Магазин электроники · PostgreSQL

Python 3.11+, PySide6, PostgreSQL.

## Получить исходники

```bash
git clone --branch postgresql https://github.com/Se7JoPa/Shop_electro.git
cd Shop_electro
```

Можно также выбрать нужную ветку на GitHub и нажать Code → Download ZIP,
затем распаковать файлы в обычную папку.

## Подготовка PostgreSQL

До первого запуска установите PostgreSQL 16 или новее.
В pgAdmin от пользователя postgres выполните каждый запрос отдельно:

```sql
CREATE ROLE electronics_app LOGIN PASSWORD 'change_this_password';
```

```sql
CREATE DATABASE electronics_shop OWNER electronics_app;
```

Замените пример пароля своим. Подключитесь к новой базе как electronics_app,
откройте schema.sql в Query Tool и выполните. Таблицы создавайте от
electronics_app (в параметрах подключения используйте имя electronics_app).
Скрипт предназначен для первого запуска в пустой базе.

Скопируйте .env.example в .env и укажите тот же пароль и параметры БД.
Запустите create_admin.py интерпретатором из .venv, затем app.py.
При вводе пароля в терминале символы не отображаются.

## Установка зависимостей и запуск

Нужен Python 3.11 или новее. Откройте терминал в папке исходников.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe create_admin.py
.\.venv\Scripts\python.exe app.py
```

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python create_admin.py
.venv/bin/python app.py
```

## Возможности

- Авторизация и регистрация, роли покупателя и администратора.
- Просмотр товаров, описаний и характеристик.
- Поиск и совместные фильтры по категории, бренду, цене и наличию.
- Добавление, редактирование и удаление товаров администратором.
- Выбор цвета интерфейса с сохранением для каждого пользователя.

## Структура базы

Пять таблиц: users, categories, brands, products, product_specs.
SQL находится в schema.sql, диаграмма в docs/ER_diagram.pdf.
Характеристики удаляются вместе с товаром. Категории и бренды можно
дополнять через редактор базы.

## Данные

Данные хранятся в PostgreSQL. Для резервного копирования используйте
pgAdmin или pg_dump. Файл .env не загружайте в репозиторий.
Если подключение не работает, убедитесь, что PostgreSQL запущена,
настройки .env совпадают с созданной базой и выполнен schema.sql.

## Доработки

Перед своими коммитами задайте имя или ник и почту:

```bash
git config user.name "ВАШЕ_ИМЯ_ИЛИ_НИК"
git config user.email "ВАША_ПОЧТА"
git add .
git commit -m "Describe your change"
git push
```

Файлы базы, .env, ключи и виртуальное окружение исключены из Git.
Перед сменой ветки остановите программу и сохраните изменения.

