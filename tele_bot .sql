CREATE DATABASE english_bot
    WITH OWNER = postgres
    ENCODING = 'UTF8'
    TEMPLATE = template0
    LC_COLLATE = 'C'
    LC_CTYPE = 'C'
    CONNECTION LIMIT = -1;
CREATE TABLE words (
    id SERIAL PRIMARY KEY,                   -- уникальный идентификатор
    target_word VARCHAR(255) NOT NULL UNIQUE, -- иностранное слово (например, английское)
    translate_word VARCHAR(255) NOT NULL     -- перевод на русский
);
INSERT INTO words (target_word, translate_word)
VALUES 
    ('apple', 'яблоко'),
    ('dog', 'собака'),
    ('house', 'дом'),
    ('car', 'машина'),
    ('book', 'книга');

SELECT * FROM words;