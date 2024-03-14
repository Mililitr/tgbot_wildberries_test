import requests
from telebot import TeleBot, types

TOKEN = 'ВАШ ТЕЛЕГРАМ ТОКЕН'
bot = TeleBot(TOKEN)

def get_product_info(article):
    url = f'https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=30&nm={article}'
    response = requests.get(url)
    if response.status_code == 200:
        product_info = response.json()
        name = product_info['data']['products'][0]['name']
        price = product_info['data']['products'][0]['salePriceU'] / 100 + product_info['data']['products'][0]['priceU'] % 100 / 100
        rating = product_info['data']['products'][0]['supplierRating']
        total_quantity = sum([sum([stock['qty'] for stock in size['stocks']]) for size in product_info['data']['products'][0]['sizes']])
        return {'name': name, 'price': price, 'rating': rating, 'available_quantity': total_quantity}
    else:
        return None

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Добро пожаловать в наш чат-бот!', reply_markup=create_menu())

def create_menu():
    markup = types.InlineKeyboardMarkup()
    item1 = types.InlineKeyboardButton("Получить информацию по товару", callback_data='product_info')
    item2 = types.InlineKeyboardButton("Остановить уведомления", callback_data='stop_notifications')
    item3 = types.InlineKeyboardButton("Получить информацию из БД", callback_data='db_info')
    markup.row(item1, item2, item3)
    return markup

import threading
import time

notification_threads = {}

class NotificationThread(threading.Thread):
    def __init__(self, bot, chat_id, article):
        threading.Thread.__init__(self)
        self.bot = bot
        self.chat_id = chat_id
        self.article = article
        self.running = True

    def run(self):
        while self.running:
            product_info = get_product_info(self.article)
            if product_info is not None:
                self.bot.send_message(self.chat_id, f"{self.article}\n"
                                                    f"Название: {product_info['name']}\n"
                                                    f"Цена: {product_info['price']}\n"
                                                    f"Рейтинг: {product_info['rating']}\n"
                                                    f"Количество товара на всех складах: {product_info['available_quantity']}",
                                                    reply_markup=create_inline_keyboard())
            time.sleep(300)

    def stop(self):
        self.running = False

def create_inline_keyboard():
    markup = types.InlineKeyboardMarkup()
    item = types.InlineKeyboardButton("Подписаться", callback_data='subscribe')
    markup.row(item)
    return markup

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == 'subscribe':
        thread = NotificationThread(bot, call.message.chat.id, call.message.text[:8])
        thread.start()
        notification_threads[call.message.chat.id] = thread
        bot.answer_callback_query(callback_query_id=call.id, text="Вы подписались на уведомления", show_alert=False)
    elif call.data == 'product_info':
        bot.send_message(call.message.chat.id, 'Введите артикул товара:')
        bot.register_next_step_handler(call.message, handle_product_id)
    elif call.data == 'stop_notifications':
        if call.message.chat.id in notification_threads:
            notification_threads[call.message.chat.id].stop()
            del notification_threads[call.message.chat.id]
            bot.answer_callback_query(callback_query_id=call.id, text="Уведомления остановлены", show_alert=False)
        else:
            bot.answer_callback_query(callback_query_id=call.id, text="Вы не подписаны на уведомления", show_alert=False)
    elif call.data == 'db_info':
        db_info = get_db_info()
        bot.send_message(call.message.chat.id, f'Информация из БД:\n{db_info}')
        bot.answer_callback_query(callback_query_id=call.id, text="Информация из БД отправлена", show_alert=False)

@bot.message_handler(func=lambda message: message.text.isdigit())
def handle_product_id(message):
    article = message.text
    product_info = get_product_info(article)
    if product_info is not None:
        bot.send_message(message.chat.id, f"{article}\n"
                                          f"Название: {product_info['name']}\n"
                                          f"Цена: {product_info['price']}\n"
                                          f"Рейтинг: {product_info['rating']}\n"
                                          f"Количество товара на всех складах: {product_info['available_quantity']}",
                                          reply_markup=create_inline_keyboard())
    else:
        bot.send_message(message.chat.id, "Товар не найден")

import sqlite3

def get_db_info():
    conn = sqlite3.connect('db.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM product ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    result = ''
    for row in rows:
        result += str(row) + '\n'

    conn.close()
    return result

bot.polling()