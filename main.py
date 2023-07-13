import logging
import sqlite3

import datetime
from aiogram import Bot, Dispatcher, executor, types

from config import token, menemi, admin_chat, path_to_db

logging.basicConfig(level=logging.INFO)

bot = Bot(token=token)
dp = Dispatcher(bot)
tz = datetime.timezone(datetime.timedelta(hours=3), name="МСК")


def log(message: types.Message):
    logs = open("logs.json", "a")
    logs.write(f"{message},\n")
    logs.close()


# ====================== Проверка, является ли юзер админом ======================
def is_admin(message: types.Message):
    connection = sqlite3.connect(path_to_db)
    cursor = connection.cursor()

    admins = cursor.execute("SELECT tg_id FROM admins").fetchall()[0]
    if admins.__contains__(str(message.from_user.id)):
        return True
    return False


# ====================== Запись полученного сообщения ======================
# Заносятся не только текстовые сообщения, но и те, что с картинками
def insert_message_in_db(message: types.Message, forwarded_message_id, text=":OnlyPicture:"):
    connection = sqlite3.connect(path_to_db)
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO requests(chat_id, message_id, username, text, forwarded_message_id) VALUES(?, ?, ?, ?, ?)",
        (str(message.chat.id), str(message.message_id), message.from_user.username, text, forwarded_message_id))
    connection.commit()
    return


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    return


# ====================== Добавление нового админа ======================
@dp.message_handler(commands=["addadmin"])
async def add_admin(message: types.Message):
    # проверка, если команду выполняю не Я, то игнорится
    if message.from_user.id != menemi:
        return

    # проверка, что у команды два аргумента (tg_id и username)
    args = message.get_args().split(" ")
    if len(args) != 2:
        await message.answer("Нужно ввести 2 аргумента: <code>{tg id}</code> <code>{username}</code>")
        return

    connection = sqlite3.connect(path_to_db)
    cursor = connection.cursor()

    # запись нового админа в бд
    tg_id = args[0]
    username = args[1].lower()
    cursor.execute(
        "INSERT INTO admins(tg_id, username) VALUES(?, ?)",
        (tg_id, username))
    connection.commit()


# ====================== Получение текстового сообщения ======================
@dp.message_handler(content_types=[types.ContentType.TEXT])
async def qa_method(message: types.Message):
    # log(message)

    # ====================== User message receiver ======================
    if not is_admin(message):
        text_answer = f"————— Обращение —————\n" \
                      f"От: @{message.from_user.username}\n" \
                      f"————————————————\n" \
                      f"{message.text}"

        # запись сообщения в бд
        forwarded_message = await bot.send_message(admin_chat,
                                                   text_answer)
        insert_message_in_db(message, f"{forwarded_message.message_id}", message.text)
        return

    # ====================== Admin message answerer ======================
    # если админ не реплайнул или написал боту НЕ в чате админов, то ответ игнорится
    if message.reply_to_message == None or message.chat.id != admin_chat:
        return

    connection = sqlite3.connect(path_to_db)
    cursor = connection.cursor()

    # 0 - message.chat.id
    # 1 - message.message_id}
    # 2 - message.from_user.username
    # 3 - text
    # 4 - forwarded_message_id
    # получение из бд сообщения когда-то отправленного пользователем
    try:
        user_message = cursor.execute(
            f"SELECT * FROM requests WHERE forwarded_message_id = '{message.reply_to_message.message_id}'").fetchall()[0]
        chat_id = user_message[0]
        text = user_message[3]
        forwarded_message_id = user_message[4]
        if text == ":OnlyPicture:":
            text = "[Фото]"

        # отправка пользователю ответа
        await bot.send_message(chat_id,
                               f"> {text}\n\n"
                               f"{message.text}")

        # удаление из бд сообщения когда-то отправленного пользователем
        cursor.execute(f"DELETE FROM requests WHERE forwarded_message_id = '{forwarded_message_id}'")
        connection.commit()
    except Exception:
        return


# ====================== Получение картинки ======================
@dp.message_handler(content_types=[types.ContentType.PHOTO])
async def photo_receiver(message: types.Message):
    # log(message)
    # если картинку прислали в чате админов, то она игнорится
    if message.chat.id == admin_chat:
        return

    # если админ отправит картинку боту в лс, то она тоже заигнорится
    if not is_admin(message):
        # сохранение фотки
        # await message.photo[-1].download("D:\\tempProjects\\python\\AbitIsSupportBot\\temp.jpg")
        await message.photo[-1].download("/home/dtitov/abit-IS-support-bot/temp.jpg")
        photo = open("/home/dtitov/abit-IS-support-bot/temp.jpg", "rb")
        text_answer = f"————— Обращение —————\n" \
                      f"От: @{message.from_user.username}\n"
        caption = ":OnlyPicture:"

        if message.caption is not None:
            text_answer += f"————————————————\n" \
                           f"{message.caption}\n" \
                           f"————————————————"
            caption = message.caption

        # запись сообщения в бд
        forwarded_message = await bot.send_photo(admin_chat,
                                                 photo,
                                                 text_answer)
        insert_message_in_db(message, str(forwarded_message.message_id), caption)


# Игнорирование любых сообщений, не являющихся текстом или картинкой
@dp.message_handler(content_types=types.ContentType.ANY)
async def echo(message: types.Message):
    return


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
