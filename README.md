# Магазин электроники

### Настольная версия · PostgreSQL

**Python 3.11+ / PySide6 / PostgreSQL**

Настольный каталог электроники с серверной базой PostgreSQL.


## Возможности

- Авторизация и роли покупателя и администратора.
- Каталог товаров, описания и характеристики.
- Поиск по названию и фильтрация по категории, бренду, цене и наличию.
- Добавление, редактирование и удаление товаров администратором.
- Персональный цвет интерфейса с сохранением в базе.

## Быстрый старт

1. Создайте базу PostgreSQL и выполните `schema.sql`, как описано в инструкции.
2. Настройте `.env` по `.env.example`.
3. Установите зависимости, создайте администратора и запустите приложение:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python create_admin.py
.venv/bin/python app.py
```

В Windows используйте `.\.venv\Scripts\python.exe` вместо `.venv/bin/python`.

## Документация

| Материал | Ссылка |
|---|---|
| Установка и работа с программой | [README_RU.md](README_RU.md) |
| ER-диаграмма базы | [Открыть PDF](docs/ER_diagram.pdf) |
| SQL-схема и примеры товаров | [schema.sql](schema.sql) |

## Другие версии

| Ветка | Приложение | База |
|---|---|---|
| [main](https://github.com/Se7JoPa/Shop_electro) | Обзор проекта и выбор версии | — |
| [postgresql](https://github.com/Se7JoPa/Shop_electro/tree/postgresql) | Настольное, PySide6 | PostgreSQL |
| [sqlite-desktop](https://github.com/Se7JoPa/Shop_electro/tree/sqlite-desktop) | Настольное, PySide6 | SQLite |
| [sqlite-web](https://github.com/Se7JoPa/Shop_electro/tree/sqlite-web) | Браузерное, Flask | SQLite |

Переключайте ветки в меню GitHub над списком файлов или командой `git switch ИМЯ_ВЕТКИ`.
Перед переключением сохраните собственные изменения и остановите программу.

