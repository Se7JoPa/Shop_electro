-- SQLite schema v1. Store initializes this atomically on first launch.
PRAGMA foreign_keys=ON;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE CHECK (length(username) BETWEEN 3 AND 50),
    password_hash TEXT NOT NULL,
    full_name VARCHAR(150) NOT NULL CHECK (length(trim(full_name)) BETWEEN 1 AND 150),
    role VARCHAR(10) NOT NULL DEFAULT 'customer'
        CHECK (role IN ('admin', 'customer')),
    accent_color VARCHAR(7) NOT NULL DEFAULT '#2563eb'
        CHECK (length(accent_color)=7 AND substr(accent_color,1,1)='#' AND substr(accent_color,2) NOT GLOB '*[^0-9a-fA-F]*'),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE brands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 200),
    description TEXT NOT NULL DEFAULT '',
    price_cents INTEGER NOT NULL CHECK (typeof(price_cents)='integer' AND price_cents BETWEEN 0 AND 999999999999),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (typeof(stock)='integer' AND stock BETWEEN 0 AND 2147483647),
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    brand_id INTEGER NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE product_specs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 100),
    value VARCHAR(500) NOT NULL CHECK (length(trim(value)) BETWEEN 1 AND 500),
    UNIQUE (product_id, name)
);
CREATE INDEX products_category_idx ON products(category_id);
CREATE INDEX products_brand_idx ON products(brand_id);
INSERT INTO categories(name) VALUES ('Смартфоны'), ('Ноутбуки'), ('Мониторы'), ('Наушники');
INSERT INTO brands(name) VALUES ('Samsung'), ('Apple'), ('Lenovo'), ('ASUS'), ('Sony');
INSERT INTO products(name, description, price_cents, stock, category_id, brand_id) VALUES
('Samsung Galaxy A55', 'Учебный пример смартфона. Цена условная.', 3499000, 12, 1, 1),
('Apple iPhone 15', 'Учебный пример смартфона. Цена условная.', 6999000, 5, 1, 2),
('Lenovo IdeaPad Slim 3', 'Ноутбук для учёбы и работы. Цена условная.', 5299000, 7, 2, 3),
('ASUS TUF Gaming', 'Игровой ноутбук. Цена условная.', 8999000, 3, 2, 4),
('Samsung Odyssey G5', 'Игровой монитор. Цена условная.', 2799000, 0, 3, 1),
('Sony WH-1000XM5', 'Беспроводные наушники. Цена условная.', 2999000, 9, 4, 5);
INSERT INTO product_specs(product_id, name, value) VALUES
(1, 'Память', '128 ГБ'), (1, 'Оперативная память', '8 ГБ'),
(2, 'Память', '128 ГБ'), (3, 'SSD', '512 ГБ'),
(4, 'Оперативная память', '16 ГБ'), (5, 'Диагональ', '27 дюймов'),
(6, 'Подключение', 'Bluetooth');
PRAGMA user_version=1;
