import random

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
import psycopg2

# Подключение к БД
conn = psycopg2.connect(
    dbname='tele_bot',
    user='postgres',
    password='1',
    host='localhost',
    port=5432
)
cursor = conn.cursor()


# Функции работы с базой
def add_word_to_db(target, translate):
    try:
        cursor.execute('INSERT INTO words (target_word, translate_word) VALUES (%s, %s)', (target, translate))
        conn.commit()
        return True
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False


def delete_word_from_db(target):
    cursor.execute('DELETE FROM words WHERE target_word = %s', (target,))
    conn.commit()


def get_random_word_with_others(n=4):
    cursor.execute('SELECT target_word, translate_word FROM words ORDER BY RANDOM() LIMIT 1')
    row = cursor.fetchone()
    if not row:
        return None

    target_word, translate_word = row
    cursor.execute('SELECT target_word FROM words WHERE target_word != %s ORDER BY RANDOM() LIMIT %s',
                   (target_word, n - 1))
    others_rows = cursor.fetchall()
    others = [w[0] for w in others_rows]
    return {
        'target_word': target_word,
        'translate_word': translate_word,
        'other_words': others
    }

print('Start telegram bot...')

state_storage = StateMemoryStorage()
token_bot = '8405586746:AAF6IcLURol9JGu59wMhHaO9TTdOwHS01yI'
bot = TeleBot(token_bot, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, "Hello, stranger, let study English...")
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []
    data = get_random_word_with_others()
    if not data:
        bot.send_message(cid, "База слов пуста. Добавьте новые слова через команду Добавить слово ➕")
        return

    target_word = data['target_word']
    translate = data['translate_word']
    others = data['other_words']
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        delete_word_from_db(target_word)
        bot.send_message(
            message.chat.id,
            f"Слово <b>{target_word}</b> успешно удалено ✅",
            parse_mode="HTML"
        )
    # После удаления сразу показываем новую карточку
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):
    cid = message.chat.id
    userStep[cid] = 1
    print(message.text)  # сохранить в БД


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            next_btn = types.KeyboardButton(Command.NEXT)
            add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)