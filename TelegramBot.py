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
bot = telebot.TeleBot(os.getenv("API_TOKEN"))
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
    bot.send_message(cid, f"Bienvenido al Bot P2P {str(nom)}, pulse \"Agregar wallet\", para iniciar la escucha de notificaciones")
    command_list(m)

def clear_message_text(message):
    # edit the message text with an empty string
    bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text='')

def default_command(cid):
    
    help_text = "Estas son las opciones disponibles:"
    # Define the buttons
    button1 = InlineKeyboardButton("Agregar Wallet", callback_data="/add_wallet")
    button2 = InlineKeyboardButton("Eliminar Wallet", callback_data="/del_wallet")
    button3 = InlineKeyboardButton("Listar mis Wallets", callback_data="/list_wallet")

    # Create a nested list of buttons
    buttons = [[button1], [button2], [button3]]

    # Create the keyboard markup
    reply_markup = InlineKeyboardMarkup(buttons)
    bot.send_message(cid, help_text, reply_markup=reply_markup)

@bot.message_handler(commands=['list'])
def command_list(m):
    cid = m.chat.id
    default_command(cid)

# Callback_Handler
# This code creates a dictionary called options that maps the call.data to the corresponding function.
# The get() method is used to retrieve the function based on the call.data. If the function exists
# , it is called passing the call.message as argument.
# This approach avoids the need to use if statements to check the value of call.data for each possible option.
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    message = call.data
    cid = call.message.chat.id
    if "/cancel" in message:
        default_command(cid)
    elif "/delete" in message:
        dels_wallets = set(message.split(" "))
        dels_wallets.remove("/delete")
        deleteWalletActions(list(dels_wallets), cid)
    
    else:
        # Define the mapping between call.data and functions
        options = {
            '/add_wallet': addWallet,
            '/del_wallet': deleteWallet,
            '/list_wallet': listWallets,
        }
        # Get the function based on the call.data
        func = options.get(call.data)

        # Call the function if it exists
        if func:
            func(call.message)

def addWallet(m):
    """
    Adds the wallet address for notifications.

    Parameters:
    - m: The message object received from the user.

    Returns:
    None
    """
    cid = m.chat.id
    markup = types.ReplyKeyboardMarkup()
    itemc = types.KeyboardButton('/cancel')
    markup.row(itemc)
    bot.send_message(cid, 'Agregar la direccón de su billetera para notificaciones', parse_mode='Markdown', reply_markup=markup)
    bot.register_next_step_handler_by_chat_id(cid, addWalletActions)

def addWalletActions(m):
    """
    Adds a wallet action based on the user input.

    Args:
        m (telegram.Message): The message object containing the user input.

    Returns:
        None
    """
    cid = m.chat.id
    valor = m.text
    if valor == '/cancel':
       markup = types.ReplyKeyboardMarkup()
       item = types.KeyboardButton('/list')
       markup.row(item)
       bot.send_message(cid, 'Seleccione una opción', parse_mode='Markdown', reply_markup=markup)
    else:
       markup = types.ReplyKeyboardMarkup()
       item = types.KeyboardButton('/list')
       markup.row(item)
       url = os.getenv("URL_ADD_WALLET_BOT")
       data = {
            "idtelegram": str(cid),
            "walletname": valor.lower()
        }
       headers = {'Content-type': 'application/json'}
       response = requests.post(url, data=json.dumps(data), headers=headers)
       # Print the status code and the response body
       if response.status_code == 200:
          bot.send_message(cid, 'Wallet agregada : ' + valor.lower(), parse_mode='Markdown', reply_markup=markup)
       else:
          bot.send_message(cid, "Error agregando Wallet", parse_mode='Markdown', reply_markup=markup)

def deleteWallet(m):
    """
    Deletes the wallet for receiving notifications.

    Args:
        m: The message object containing the chat information.

    Returns:
        None
    """
    try:
        cid = m.chat.id
        
        help_text = "*Selecciona un wallet para eliminar:*"
        # Define the buttons
        buttons = []
        response_data = requests.post(os.getenv("URL_LIST_WALLET_BOT"), data=json.dumps({"idtelegram": str(cid)}), headers={'Content-type': 'application/json'}).json()
        if 'data' in response_data:
            for item in response_data['data']:
                buttons.append([InlineKeyboardButton(str(item['walletname']), callback_data=f"/delete {str(item['walletname'])}")])

        # Create the keyboard markup
        reply_markup = InlineKeyboardMarkup(buttons)
        bot.send_message(cid, help_text, reply_markup=reply_markup)
        # bot.register_next_step_handler_by_chat_id(cid, deleteWalletActions)
        
        # markup = types.ReplyKeyboardMarkup()
        # itemc = types.KeyboardButton('CANCEL')
        # markup.row(itemc)
        # bot.send_message(cid, 'Coloque la direccón de su billetera para dejar de recibir notificaciones', parse_mode='Markdown', reply_markup=markup)
    except Exception as e: print(e)

def deleteWalletActions(wallets, cid):
    """
    Perform actions to delete wallets by name (List or not).

    Args:
        wallets: A list of user wallets names registered.

    Returns:
        None
    """
    
    removes = ""
    failures = ""
    url = os.getenv("URL_DELETE_WALLET_BOT")
    if not isinstance(wallets, list): wallets = [wallets]
    for wallet in wallets:
        wallet_name = wallet.lower()
        data = {"idtelegram": str(cid), "walletname": wallet_name}
        headers = {'Content-type': 'application/json'}
        response = requests.post(url, data=json.dumps(data), headers=headers)
        if response.status_code == 200:
            if removes: removes += f", {wallet_name}"
            removes = wallet_name
        else:
            if failures: failures += f", {wallet_name}"
            failures = wallet_name
    
    markup = types.ReplyKeyboardMarkup()
    item = types.KeyboardButton('/list')
    markup.row(item)
    bot.send_message(cid, (f" - *Wallets eliminadas (Exito):* {removes} " if removes else "- *Ninguna wallet fue eliminada.*") + (f" - *Walets no eliminadas (Error):* {failures}" if failures else ""), parse_mode='Markdown', reply_markup=markup)
    # bot.send_message(cid, "Error agregando Wallet", parse_mode='Markdown', reply_markup=markup)


def listWallets(m):
    """
    Retrieves a list of wallets from the NearP2P API and sends it as a message to the user.

    Args:
        m: The message object received from the user.

    Returns:
        None
    """
    cid = m.chat.id
    bot.send_message(cid, "*Lista de wallets agregadas:*", parse_mode='Markdown')
    
    try:
        response = requests.post(os.getenv("URL_LIST_WALLET_BOT"), data=json.dumps({"idtelegram": str(cid)}), headers={'Content-type': 'application/json'})
        if response.status_code == 200:
            response_data = response.json()
            if 'data' in response_data:
                for item in response_data['data']:
                    bot.send_message(cid, f"*Wallet:* {str(item['walletname'])}", parse_mode='Markdown')
            else:
                bot.send_message(cid, "No wallets found.", parse_mode='Markdown')
        else:
            bot.send_message(cid, f"API Error: {response.status_code} - {response.text}", parse_mode='Markdown')
    except requests.exceptions.JSONDecodeError:
        bot.send_message(cid, "Error: Invalid response from API.", parse_mode='Markdown')
    except Exception as e:
        bot.send_message(cid, f"Unexpected error: {str(e)}", parse_mode='Markdown')
    
    markup = types.ReplyKeyboardMarkup()
    item = types.KeyboardButton('/list')
    markup.row(item)
    bot.send_message(cid, "Listado finalizado..", reply_markup=markup)


# default handler for every other text
@bot.message_handler(func=lambda message: True, content_types=['text'])
def command_default(m):
    # this is the standard reply to a normal message
    markup = types.ReplyKeyboardMarkup()
    iteme = types.KeyboardButton('/list')
    markup.row(iteme)
    bot.send_message(m.chat.id, "Does not understand \"" + m.text + "\"\n , try with \n \n /list" , reply_markup=markup)

bot.infinity_polling()
