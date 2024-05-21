
import requests, json, os, telebot, sys
from dotenv import load_dotenv
load_dotenv()
API_TOKEN = str(os.getenv("API_TOKEN"))

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
              

def get_transactions():
    
    query = """
    query MyQuery {
        ordersells {
            order_id
            owner_id
            signer_id
            status
        }
        orderbuys {
            order_id
            owner_id
            signer_id
            status
        }
        orderhistorysells { 
            status
            signer_id
            owner_id
            order_id
        }
        orderhistorybuys { 
            status
            signer_id
            owner_id
            order_id
        }
    }
    """

    return requests.post(os.getenv("URL_SUBGRAPHS_P2P"), headers={'Content-Type': 'application/json'}, json={'query': query}).json().get("data")

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
    
def verify_transactions():
    try:
        active_transactions = get_transactions()
        list_wallet_bot = []
        bot = None
        
        if active_transactions.get("ordersells") or active_transactions.get("orderbuys"):
            bot = telebot.TeleBot(API_TOKEN)
            
            list_wallet_bot = requests.post(os.getenv("URL_LIST_WALLET_BOT"), headers = {'Content-type': 'application/json'}).json().get("data")
            
            notify_new_transaction = []
            
            add_transactions(active_transactions.get("ordersells") or [], list_wallet_bot, notify_new_transaction, "sell")
            add_transactions(active_transactions.get("orderbuys") or [], list_wallet_bot, notify_new_transaction, "buy")

            for wallets in notify_new_transaction:
                tipo = 'venta' if wallets['tipo'] == 'sell' else 'compra'
                if wallets.get("chat_owner"): bot.send_message(chat_id = wallets["chat_owner"], text = generate_msg_new(wallets.get("order_id"), wallets['wallet_owner'], tipo))
                if wallets.get("chat_signer"): bot.send_message(chat_id = wallets["chat_signer"], text = generate_msg_new(wallets.get("order_id"), wallets['wallet_signer'], tipo))
                
        pendings = get_all()
        if len(pendings) > 0: # verify_historical_sells or verify_historical_buys
            if not bot:
                bot = telebot.TeleBot(API_TOKEN)
            
            if len(list_wallet_bot) == 0:
                list_wallet_bot = requests.post(os.getenv("URL_LIST_WALLET_BOT"), headers = {'Content-type': 'application/json'}).json().get("data")
            
            historical_transactions = get_historical(active_transactions, pendings)
            
            notify_update_transaction = []
            if historical_transactions:
                
                add_historical(historical_transactions.get("orderhistorysells") or [], list_wallet_bot, notify_update_transaction, "sell")
                add_historical(historical_transactions.get("orderhistorybuys") or [], list_wallet_bot, notify_update_transaction, "buy")
                
            for wallets in notify_update_transaction:
                tipo = 'venta' if wallets['tipo'] == 'sell' else 'compra'
                if wallets["chat_owner"]: bot.send_message(chat_id = wallets["chat_owner"], text = generate_msg_hist(wallets.get("order_id"), wallets["wallet_owner"], wallets.get("modify_to"), tipo))
                if wallets["chat_signer"]: bot.send_message(chat_id = wallets["chat_signer"], text = generate_msg_hist(wallets.get("order_id"), wallets['wallet_signer'], wallets.get("modify_to"), tipo))
                    
    except: generate_err(sys.exc_info())
        
def generate_msg_hist(order_id, name, to_modify, tipo):
    if to_modify == 3:
        return f"Su orden de {tipo} N°{order_id} de la wallet {name} ha entrado en disputa, por favor verificar o contactar a soporte https://t.me/nearp2p."
    elif to_modify == 4:
        return f"Su orden de {tipo} N°{order_id} de la wallet {name} ha sido cancelada."
    
    return f"🥳 Felicitaciones su orden de {tipo} N°{order_id} de la wallet {name} ha finalizado con éxito."

def generate_msg_new(order_id, name, tipo):
    return f"Se ha generado la orden de {tipo} N°{order_id} de intercambio para {name} por favor verificar."
