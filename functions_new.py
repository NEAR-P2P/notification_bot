
import requests, json, os, telebot, sys
from dotenv import load_dotenv
import asyncio
from gql import Client, gql
from gql.transport.websockets import WebsocketsTransport
from websockets.exceptions import ConnectionClosedError
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
bot = telebot.TeleBot(API_TOKEN)
type = "Venta"
# Check if the order_id exists in the history sell and history buys
counter = {}
api_chat_id = None
# Initialize a session dictionary
chat_session = {}
# Define counters
counter['counterNumber'] = 0
counter['counterNumberHistory'] = 0
counter['counterNumberDispute'] = 0

def type_err(estatus):
    if estatus in [401, 402, 403, 407, 423, 451]:
        return f" {estatus} - Error de autorización."
    elif estatus in [404, 405, 501, 503]:
        return f" {estatus} - Solicitud no disponible."
    else: return f" {estatus} - Error de ejecucion."
    
def generate_err(exc_info, estatus = 500, imprimir = True):
    data_error = os.path.split(exc_info[2].tb_frame.f_code.co_filename)
    error_a = 'Hubo el error: "%s".; %s; '%(exc_info[1], type_err(estatus))
    error_b = 'Ubicacion "%s", archivo "%s", linea "%s", tipo "%s"'%(data_error[0], data_error[1], exc_info[2].tb_lineno, exc_info[0].__doc__)
    if imprimir: print(error_a, error_b)
    return error_a + error_b

class ActiveTransactions():
    new = True
    modify = False
    delete = False
    json = {}
    
    def __init__(self, *args, **kwargs):
        new_obj = kwargs.get('json')
        
        save_data = open("json_transactions.json", "r")
        try: actives = json.load(save_data)
        except: actives = [new_obj]
        for i, objs in enumerate(actives):
            if objs.get('order_id') == new_obj.get('order_id'):
                self.new = False
                if objs.get('estado') != objs.get('estado'):
                    self.modify = True; indice = i
                if new_obj.get('historical'):
                    self.delete = True; indice = i
        if self.new: actives.append(new_obj)
        if self.modify: actives[indice] = new_obj
        if self.delete: del actives[indice]
        save_data.close()
        
        
        save_file = open("json_transactions.json", "w")
        json.dump(actives, save_file, indent = 4)
        save_file.close()
        
def get_all():
    objs = []
    try: actives = json.load(open("json_transactions.json", "r"))
    except: actives = []
    for obj in actives:
        objs.append(obj)
    return objs

def filter_transactions(field, value, objs):
    fitered = []
    for obj in objs:
        if obj[field] == value:
            fitered.append(obj)
    return fitered

def add_transactions(active_transactions, list_wallet_bot, notify_new_transaction, tipo):
    for transaction in active_transactions:
        active_data_owner = {}
        active_data_signer = {}
        for person in list_wallet_bot:
            if person.get("walletname") == transaction.get("owner_id"):
                active_data_owner = {"wallet": transaction["owner_id"], "telegram_chat": person['idtelegram']}
            if person.get("walletname") == transaction.get("signer_id"):
                active_data_signer = {"wallet": transaction["signer_id"], "telegram_chat": person['idtelegram']}
        
        if active_data_owner or active_data_signer:
            obj = ActiveTransactions(json = {"tipo": tipo, "order_id": transaction["order_id"], "signer": active_data_signer.get("wallet"), "owner": active_data_owner.get("wallet"), "estado": transaction["status"]})
            if obj.new or obj.modify:
                notify_new_transaction.append({"order_id": transaction["order_id"], "wallet_owner": active_data_owner.get("wallet"), "chat_owner": active_data_owner.get("telegram_chat"), "wallet_signer": active_data_signer.get("wallet"), "chat_signer": active_data_signer.get("telegram_chat"), "tipo": tipo, "modify_to": transaction["status"] if obj.modify else None})
                
def add_historical(historical_transactions, list_wallet_bot, notify_update_transaction, tipo):
    for history in historical_transactions:
        historical_data_owner = {}
        historical_data_signer = {}
        for person in list_wallet_bot:
            if person.get("walletname") == history.get("owner_id"):
                historical_data_owner = {"wallet": history["owner_id"], "telegram_chat": person['idtelegram']}
            if person.get("walletname") == history.get("signer_id"):
                historical_data_signer = {"wallet": history["signer_id"], "telegram_chat": person['idtelegram']}
                
        if historical_data_owner or historical_data_signer:
            obj = ActiveTransactions(json = {"tipo": tipo, "order_id": history["order_id"], "signer": historical_data_signer.get("wallet"), "owner": historical_data_owner.get("wallet"), "estado": history["status"], "historical": True,})
            if obj.delete:
                notify_update_transaction.append({"order_id": history["order_id"], "wallet_owner": historical_data_owner.get("wallet"), "chat_owner": historical_data_owner.get("telegram_chat"), "wallet_signer": historical_data_signer.get("wallet"), "chat_signer": historical_data_signer.get("telegram_chat"), "tipo": tipo, "modify_to": history.get("status")})
              
# Initialize a session dictionary with lists
varsession = {
    'ordersells': [],
    'orderbuys': [],
    'orderhistorysells': [],
    'orderhistorybuys': [],
}

# web socket handle
def get_websocket_url(http_url):
    """
    Converts an HTTP URL to a WebSocket URL by replacing the scheme.

    Args:
        http_url (str): The HTTP URL to convert.

    Returns:
        str: The WebSocket URL.

    Raises:
        ValueError: If the URL scheme is invalid (not http or https).
    """
    if http_url.startswith("https://"):
        return http_url.replace("https://", "wss://")
    elif http_url.startswith("http://"):
        return http_url.replace("http://", "ws://")
    else:
        raise ValueError("Invalid URL scheme. Must be http or https.")

# suscribe where the graphql query is the subscription and the field is the key of the result
# storing in a session variable
async def subscribe_to_field(ws_url, query, field, callback):
    """
    Subscribes to a specific field in a WebSocket connection and invokes a callback function
    whenever a new result is received.

    Args:
        ws_url (str): The URL of the WebSocket connection.
        query (str): The query to subscribe to.
        field (str): The field to monitor in the results.
        callback (function): The callback function to invoke when a new result is received.
            The function should accept the following parameters:
                - field (str): The field being monitored.
                - order_id (str): The order ID extracted from the result.
                - status (str): The status extracted from the result.
                - signer_id (str): The signer ID extracted from the result.
                - owner_id (str): The owner ID extracted from the result.

    Raises:
        ConnectionClosedError: If the WebSocket connection is closed unexpectedly.
        Exception: If any other error occurs during the subscription.

    Returns:
        None
    """
    while True:
        try:
            transport = WebsocketsTransport(url=ws_url)
            client = Client(transport=transport, fetch_schema_from_transport=False)

            async with client as session:
                async for result in session.subscribe(query):
                    if field in result:
                        for item in result[field]:
                            order_id = item.get('order_id')
                            status = item.get('status')
                            signer_id = item.get('signer_id')
                            owner_id = item.get('owner_id')
                            # Append the order_id to the appropriate list in the session variable
                            varsession[field].append(order_id)
                            callback(field, order_id, status, signer_id, owner_id)
        except ConnectionClosedError as e:
            # print(f"Connection closed with error: {e}. Reconnecting...")
            await asyncio.sleep(1)  # Wait before retrying
        except Exception as e:
            print(f"An error occurred: {e}")
            await asyncio.sleep(1)  # Wait before retrying

# graphql to get the transactions
async def get_transactions(callback):
    """
    Subscribes to various GraphQL subscriptions for transaction data and invokes the provided callback function for each received transaction.

    Args:
        callback (function): The callback function to be invoked for each received transaction.

    Returns:
        None
    """
    http_url = os.getenv("URL_SUBGRAPHS_P2P")
    ws_url = get_websocket_url(http_url)
    
    queries = {
        'ordersells': gql("""
            subscription {
                ordersells {
                    order_id
                    owner_id
                    signer_id
                    status
                }
            }
        """),
        'orderbuys': gql("""
            subscription {
                orderbuys {
                    order_id
                    owner_id
                    signer_id
                    status
                }
            }
        """),
        'orderhistorysells': gql("""
            subscription {
                orderhistorysells (first: 100, orderBy: order_id, orderDirection: desc) {
                    status
                    signer_id
                    owner_id
                    order_id
                }
            }
        """),
        'orderhistorybuys': gql("""
            subscription {
                orderhistorybuys (first: 100, orderBy: order_id, orderDirection: desc) {
                    status
                    signer_id
                    owner_id
                    order_id
                }
            }
        """)
    }

    # This line of code is a list comprehension in Python, which is a concise way to create lists. It's creating a list of tasks, where each task is a subscription to a field in a WebSocket connection.
    # The subscribe_to_field function is being called for each field in queries. The arguments passed to subscribe_to_field are:
    # ws_url: The URL of the WebSocket connection.
    # queries[field]: The query associated with the current field. queries is a dictionary where the keys are field names and the values are the corresponding queries.
    # field: The current field name.
    # callback: A callback function that will be invoked whenever a new result is received from the subscription.
    # The subscribe_to_field function is asynchronous, which means it returns a coroutine object that can be awaited to get the result. In this case, the result of the function is not being used, but the coroutine objects are being stored in the tasks list. This is likely because the tasks will be run concurrently later using an asyncio function like asyncio.gather(*tasks).
    # The subscribe_to_field function itself is a loop that continuously subscribes to updates from the WebSocket connection and invokes the callback function whenever a new result is received. If the WebSocket connection is closed unexpectedly, it waits for a second and then tries to reconnect. If any other error occurs, it prints the error message, waits for a second, and then retries.
    tasks = [subscribe_to_field(ws_url, queries[field], field, callback) for field in queries]
    await asyncio.gather(*tasks)

# handle update read the session variables and filter the order_id to search in history or actual
# is the function thta will send the message to the bot
# Angel --------------------------------- Here handle the message bot
def handle_update(source, order_id, status, signer_id, owner_id):
    """
    Handle an update for a given order.

    Args:
        source (str): The source of the update.
        order_id (str): The ID of the order.
        status (str): The status of the order.
        signer_id (str): The ID of the signer.
        owner_id (str): The ID of the owner.

    Returns:
        None
    """
    # Assuming session is a global variable
    global varsession, chat_session, counter

    if source == 'ordersells' or source == 'orderhistorysells':
       type = "Venta"
    else: 
       type = "Compra" 

    # Get the user chatid
    # Avoid multiple requests to the API
    # print("api chat id", chat_session.get('api_chat_id'))
    if chat_session.get('api_chat_id') is None:
        params = {
            "walletname": signer_id
        }

        response = requests.post(
            os.getenv("URL_LIST_WALLET_BOT"), 
            headers={'Content-type': 'application/json'}, 
            json=params
        ).json()

        chat_session['api_chat_id'] = response.get("data")[0].get("idtelegram")

    # print(chat_session['api_chat_id'])

    if source in ['orderhistorysells', 'orderhistorybuys']:
        if order_id in varsession['ordersells'] or order_id in varsession['orderbuys']:
            if 'counterNumberHistory' in counter and counter['counterNumberHistory'] == 0:
                # print(f"Source: {source}, Order ID: {order_id}, Status: {status}", f"Signer ID: {signer_id}, Owner ID: {owner_id}")
                bot.send_message(chat_id = chat_session['api_chat_id'], text = generate_msg_hist(order_id, signer_id, status, type))
                counter['counterNumberHistory'] = 1
                counter['counterNumber'] = 0
            # Remove the session Variable order id
            if order_id in varsession['ordersells']: 
                varsession['ordersells'].remove(order_id) 
                counter['counterNumber'] = 0 
                counter['counterNumberDispute'] = 0    
            else: 
                varsession['orderbuys'].remove(order_id)
                counter['counterNumber'] = 0   
                counter['counterNumberDispute'] = 0
    elif source in ['ordersells', 'orderbuys']:    
        if status == 3 and 'counterNumberDispute' in counter and counter['counterNumberDispute'] == 0:
            counter['counterNumber'] = 0 
            counter['counterNumberDispute'] = 1
        if 'counterNumber' in counter and counter['counterNumber'] == 0:
            # print(f"Source: {source}, Order ID: {order_id}, Status: {status}", f"Signer ID: {signer_id}, Owner ID: {owner_id}")
            bot.send_message(chat_id = chat_session['api_chat_id'], text = generate_msg_new(order_id, signer_id, type, status))
            counter['counterNumber'] = 1  
            counter['counterNumberHistory'] = 0
    # print(counter)        
# def to verify the transaction        
async def verify_transactions():
    """
    Verifies transactions by calling the `get_transactions` function and handling the update.

    Raises:
        Exception: If an error occurs during the verification process.
    """
    try:
        await get_transactions(handle_update)
    except Exception as e: 
        print(f"An error occurred: {e}")


def filter_his(type, objects, all_pendings, retorno):
    obj_by_type = lambda lista: [o.get("order_id") for o in lista if o['tipo'] == type]
    pendings = obj_by_type(all_pendings)
    for obj in objects:
        if obj.get('order_id') in pendings:
            retorno.append(obj)

def get_historical(objects, all_pendings):
    retorno = {"orderhistorysells": [], "orderhistorybuys": []}
    filter_his("sell", objects.get("orderhistorysells"), all_pendings, retorno['orderhistorysells'])
    filter_his("buy", objects.get("orderhistorybuys"), all_pendings, retorno['orderhistorybuys'])
    return retorno
    
# def verify_transactions():
#     try:
#         active_transactions = get_transactions()
#         list_wallet_bot = []
        
#         if active_transactions.get("ordersells") or active_transactions.get("orderbuys"):
#             bot = telebot.TeleBot(API_TOKEN)
            
#             list_wallet_bot = requests.post(os.getenv("URL_LIST_WALLET_BOT"), headers = {'Content-type': 'application/json'}).json().get("data")
            
#             notify_new_transaction = []
            
#             add_transactions(active_transactions.get("ordersells") or [], list_wallet_bot, notify_new_transaction, "sell")
#             add_transactions(active_transactions.get("orderbuys") or [], list_wallet_bot, notify_new_transaction, "buy")

#             for wallets in notify_new_transaction:
#                 tipo = 'venta' if wallets['tipo'] == 'sell' else 'compra'
#                 if wallets.get("chat_owner"): bot.send_message(chat_id = wallets["chat_owner"], text = generate_msg_new(wallets.get("order_id"), wallets['wallet_owner'], tipo))
#                 if wallets.get("chat_signer"): bot.send_message(chat_id = wallets["chat_signer"], text = generate_msg_new(wallets.get("order_id"), wallets['wallet_signer'], tipo))
                
#         pendings = get_all()
#         if len(pendings) > 0: # verify_historical_sells or verify_historical_buys
#             bot = telebot.TeleBot(API_TOKEN)
            
#             if len(list_wallet_bot) == 0:
#                 list_wallet_bot = requests.post(os.getenv("URL_LIST_WALLET_BOT"), headers = {'Content-type': 'application/json'}).json().get("data")
            
#             historical_transactions = get_historical(active_transactions, pendings)
            
#             notify_update_transaction = []
#             if historical_transactions:
                
#                 add_historical(historical_transactions.get("orderhistorysells") or [], list_wallet_bot, notify_update_transaction, "sell")
#                 add_historical(historical_transactions.get("orderhistorybuys") or [], list_wallet_bot, notify_update_transaction, "buy")
                
#             for wallets in notify_update_transaction:
#                 tipo = 'venta' if wallets['tipo'] == 'sell' else 'compra'
#                 if wallets["chat_owner"]: bot.send_message(chat_id = wallets["chat_owner"], text = generate_msg_hist(wallets.get("order_id"), wallets["wallet_owner"], wallets.get("modify_to"), tipo))
#                 if wallets["chat_signer"]: bot.send_message(chat_id = wallets["chat_signer"], text = generate_msg_hist(wallets.get("order_id"), wallets['wallet_signer'], wallets.get("modify_to"), tipo))
                    
#     except: generate_err(sys.exc_info())

        
def generate_msg_hist(order_id, name, to_modify, tipo):
    if to_modify == 3:
        return f"🥳 Felicitaciones su orden de {tipo} N°{order_id} ha finalizado con éxito."
    elif to_modify == 4:
        return f"Orden de {tipo} N°{order_id} de la wallet **{name}** ha sido cancelada."
    
    return f"🥳 Felicitaciones su orden de {tipo} N°{order_id} ha finalizado con éxito."

def generate_msg_new(order_id, name, tipo, status):
    if status == 3:
        return f"Orden de {tipo} N°{order_id} de la wallet **{name}** ha entrado en disputa, por favor verificar o contactar a soporte\n\nhttps://t.me/nearp2p."
    else:
        return f"Se ha generado la orden de {tipo} N°{order_id} de intercambio para\n \n**{name}**\n \npor favor verificar.\n\n{os.getenv('URL_WALLET_P2P_AREPITA')}\n\nTambién pude verificar en NEAR P2P\n\n{os.getenv('URL_NEAR_P2P')}"