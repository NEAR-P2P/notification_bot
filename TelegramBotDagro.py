import os
from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json

# loading the .env file
load_dotenv()


# Telegram Bot
bot = telebot.TeleBot(os.getenv("API_TOKEN_DAGRO"))
########################################################################################################
###############################Operaciones para manejar en el Bot#######################################
########################################################################################################

# only used for console output now
def listener(messages):
    """
    When new messages arrive TeleBot will call this function.
    """
    #    for m in messages:
    #        if m.content_type == 'text':
    #            print(str(m.chat.first_name) + " [" + str(m.chat.id) + "]: " + m.text)

    bot.set_update_listener(listener)  # register listener


# Comando inicio
@bot.message_handler(commands=['start'])
def command_start(m):
    cid = m.chat.id
    nom = m.chat.first_name
    bot.send_message(cid, f"Bienvenido al Bot Dagro, su Telegram Id para recibir notificaciones es: {str(cid)} n\n\ Dirígase a su wallet dagro y edite en mi perfil la opción de Telegram Handler")

def clear_message_text(message):
    # edit the message text with an empty string
    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text='')


# default handler for every other text
@bot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(m):
    # this is the standard reply to a normal message
    markup = types.ReplyKeyboardMarkup()
    iteme = types.KeyboardButton('/list')
    markup.row(iteme)
    bot.send_message(m.chat.id, "Does not understand \"" + m.text + "\"\n , try with \n \n /list" , reply_markup=markup)

bot.infinity_polling()
