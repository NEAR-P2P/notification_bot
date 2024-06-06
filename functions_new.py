
import requests, json, os, telebot, sys
from dotenv import load_dotenv
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
bot = telebot.TeleBot(API_TOKEN)


def handle_update(order_id, status, signer_id, owner_id, type):
    """
    Handle an update for a given order.

    Args:
        order_id (str): The ID of the order.
        status (str): The status of the order.
        signer_id (str): The ID of the signer.
        owner_id (str): The ID of the owner.

    Returns:
        None
    """

    # Get the user chatid
    params = {
        "walletname": signer_id
    }
    response = requests.post(
        os.getenv("URL_LIST_WALLET_BOT"), 
        headers={'Content-type': 'application/json'}, 
        json=params
    ).json()

    data = response.get("data")
    if data and len(data) > 0:
        print(1)
        bot.send_message(chat_id = data[0].get("idtelegram"), text = generate_msg_new(order_id, data[0].get("walletname"), type, status))

    params1 = {
        "walletname": owner_id
    }

    response1 = requests.post(
        os.getenv("URL_LIST_WALLET_BOT"), 
        headers={'Content-type': 'application/json'}, 
        json=params1
    ).json()

    data1 = response1.get("data")
    if data1 and len(data1) > 0:
        print(2)
        bot.send_message(chat_id = data1[0].get("idtelegram"), text = generate_msg_new(order_id, data1[0].get("walletname"), type, status))


def generate_msg_new(order_id, name, tipo, status):
    if status == 3:
        return f"Orden de {tipo} N°{order_id} de la wallet **{name}** ha entrado en disputa, por favor verificar o contactar a soporte\n\nhttps://t.me/nearp2p."
    elif status == 4:
        return f"Orden de {tipo} N°{order_id} de la wallet **{name}** ha sido cancelada."
    elif status == 5:
        return f"🥳 Felicitaciones su orden de {tipo} N°{order_id} ha finalizado con éxito."   
    else:
        return f"Se ha generado la orden de {tipo} N°{order_id} de intercambio para\n \n**{name}**\n \npor favor verificar.\n\n{os.getenv('URL_WALLET_P2P_AREPITA')}\n\nTambién pude verificar en NEAR P2P\n\n{os.getenv('URL_NEAR_P2P')}"
