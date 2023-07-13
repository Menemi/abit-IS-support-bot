import sqlite3

connection = sqlite3.connect("database.db")
cursor = connection.cursor()

cursor.execute("create table if not exists requests"
               "("
               "chat_id    text not null,"
               "message_id text not null"
               ");")

cursor.execute("create table if not exists admins"
               "("
               "    tg_id    text not null,"
               "    username text not null"
               ");")
