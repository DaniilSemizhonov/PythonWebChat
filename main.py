import asyncio
import hashlib
from pymongo import MongoClient
from pywebio import start_server
from pywebio.input import *
from pywebio.output import *
from pywebio.session import defer_call, info as session_info, run_async, run_js

client = MongoClient('myfunserver.paradoxmedia.space', 31602, tls=True)
client.the_database.authenticate('albert56454', 'Der.Deb.Expl.D/j/0', source='admin', mechanism='SCRAM-SHA-1')
db = client['MessengerDB']
all_users_collection = db['all_users']

def insert_document(collection, data):
    return collection.insert_one(data).inserted_id

def find_document(collection, elements, multiple=False):
    if multiple:
        results = collection.find(elements)
        return [r for r in results]
    else:
        return collection.find_one(elements)

def update_document(collection, query_elements, new_values):
    collection.update_one(query_elements, {'$set': new_values})

def auth_user(nick, password):
    user = find_document(all_users_collection, {'nick': nick})
    if user:
        oldpass = user['password']
        entpass = hashlib.md5(password.encode())
        if oldpass == entpass.hexdigest():
            return 2
        else:
            return 0
    else:
        return 1

def register_user(nick, password):
    user_ex = find_document(all_users_collection, {'nick': nick})
    if user_ex:
        return 0
    else:
        passwrd = hashlib.md5(password.encode())
        new_user = {
            'nick': nick,
            'password':passwrd.hexdigest()
        }
        insert_document(all_users_collection, new_user)
        return 1

def validate1(n):
    if n["act"] == "Войти":
        if auth_user(n['nickname'], n['password']) == 2:
            return None
        if auth_user(n['nickname'], n['password']) == 0:
            return "password", "Неверный пароль!"
        if auth_user(n['nickname'], n['password']) == 1:
            return "nickname", "Такого пользователя не существует!"
    else:
        if n["act"] == "Зарегестироваться":
            if register_user(n['nickname'], n['password']) == 0:
                return "nickname", "Имя используеться!"
            if register_user(n['nickname'], n['password']) == 1:
                return None


chat_msgs = []
online_users = set()


MAX_MESSAGES_COUNT = 1000


async def main():
    global chat_msgs

    put_markdown("## Hello world")

    msg_box = output()
    put_scrollable(msg_box, height=300, keep_bottom=True)

    auth = await input_group("Войти в чат", [
                input("Ваше имя", required=True, name="nickname"),
                input("Ваш пароль", required=True, name="password"),
                actions(name="act", buttons=["Войти", "Зарегестироваться"])
            ], validate=validate1)
    nickname = auth['nickname']
    online_users.add(nickname)

    chat_msgs.append(('📢', f'`{nickname}` присоединился к чату!'))
    msg_box.append(put_markdown(f'📢 `{nickname}` присоединился к чату'))

    refresh_task = run_async(refresh_msg(nickname, msg_box))

    while True:
        data = await input_group("💭 Новое сообщение", [
            input(placeholder="Текст сообщения ...", name="msg"),
            actions(name="cmd", buttons=["Отправить", {'label': "Выйти из чата", 'type': 'cancel'}])
        ], validate=lambda m: ('msg', "Введите текст сообщения!") if m["cmd"] == "Отправить" and not m['msg'] else None)

        if data is None:
            break

        msg_box.append(put_markdown(f"`{nickname}`: {data['msg']}"))
        chat_msgs.append((nickname, data['msg']))

    refresh_task.close()

    online_users.remove(nickname)
    toast("Вы вышли из чата!")
    msg_box.append(put_markdown(f'📢 Пользователь `{nickname}` покинул чат!'))
    chat_msgs.append(('📢', f'Пользователь `{nickname}` покинул чат!'))

    put_buttons(['Перезайти'], onclick=lambda btn: run_js('window.location.reload()'))


async def refresh_msg(nickname, msg_box):
    global chat_msgs
    last_idx = len(chat_msgs)

    while True:
        await asyncio.sleep(1)

        for m in chat_msgs[last_idx:]:
            if m[0] != nickname:  # if not a message from current user
                msg_box.append(put_markdown(f"`{m[0]}`: {m[1]}"))

        # remove expired
        if len(chat_msgs) > MAX_MESSAGES_COUNT:
            chat_msgs = chat_msgs[len(chat_msgs) // 2:]

        last_idx = len(chat_msgs)


if __name__ == "__main__":
    start_server(main, debug=True, port=8070, cdn=False)
