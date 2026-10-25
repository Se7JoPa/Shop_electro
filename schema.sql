-- PostgreSQL. Run against an empty electronics_shop database.
BEGIN;
CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    role VARCHAR(10) NOT NULL DEFAULT 'customer'
        CHECK (role IN ('admin', 'customer')),
    accent_color VARCHAR(7) NOT NULL DEFAULT '#2563eb'
        CHECK (accent_color ~ '^#[0-9a-fA-F]{6}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE categories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE brands (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(200) NOT NULL CHECK (length(trim(name)) > 0),
    description TEXT NOT NULL DEFAULT '',
    price NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    category_id BIGINT NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE product_specs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL CHECK (length(trim(name)) > 0),
    value VARCHAR(500) NOT NULL CHECK (length(trim(value)) > 0),
    UNIQUE (product_id, name)
);
CREATE INDEX products_category_idx ON products(category_id);
CREATE INDEX products_brand_idx ON products(brand_id);
INSERT INTO categories(name) VALUES ('Смартфоны'), ('Ноутбуки'), ('Мониторы'), ('Наушники');
INSERT INTO brands(name) VALUES ('Samsung'), ('Apple'), ('Lenovo'), ('ASUS'), ('Sony');
INSERT INTO products(name, description, price, stock, category_id, brand_id) VALUES
('Samsung Galaxy A55', 'Учебный пример смартфона. Цена условная.', 34990, 12, 1, 1),
('Apple iPhone 15', 'Учебный пример смартфона. Цена условная.', 69990, 5, 1, 2),
('Lenovo IdeaPad Slim 3', 'Ноутбук для учёбы и работы. Цена условная.', 52990, 7, 2, 3),
('ASUS TUF Gaming', 'Игровой ноутбук. Цена условная.', 89990, 3, 2, 4),
('Samsung Odyssey G5', 'Игровой монитор. Цена условная.', 27990, 0, 3, 1),
('Sony WH-1000XM5', 'Беспроводные наушники. Цена условная.', 29990, 9, 4, 5);
INSERT INTO product_specs(product_id, name, value) VALUES
(1, 'Память', '128 ГБ'), (1, 'Оперативная память', '8 ГБ'),
(2, 'Память', '128 ГБ'), (3, 'SSD', '512 ГБ'),
(4, 'Оперативная память', '16 ГБ'), (5, 'Диагональ', '27 дюймов'),
(6, 'Подключение', 'Bluetooth');
COMMIT;
