
import requests, json, os, telebot, sys

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
        
        # actives = open("active_transactions.txt", "r+")
        # data_into_list = actives.readlines()
        # linea = None
        # for i, obj in enumerate(data_into_list):
        #     obj = json.loads(obj)
        #     if obj['order_id'] == new_obj['order_id'] and obj['tipo'] == new_obj['tipo']:
        #         self.new = False
        #         linea = (i, obj['estado'], new_obj['estado'], new_obj.get("historical"))
        
        # if linea != None and linea[1] != linea[2] and not linea[3]:
        #     data_into_list[linea[0]] = json.dumps(new_obj)+("\n" if len(data_into_list) > 0 else "")
        #     actives.truncate(0)
        #     actives.seek(0)
        #     actives.writelines(data_into_list)
        #     self.modify = True
            
        # elif linea != None and linea[3]:
        #     self.finnish = True
        #     del data_into_list[linea[0]]
        #     actives.truncate(0)
        #     if data_into_list:
        #         actives.seek(0)
        #         actives.writelines(data_into_list)
            
        # if self.new:
        #     new_data = actives.readlines()
        #     actives.write(("\n" if len(data_into_list) > 0 else "")+json.dumps(new_obj))
        
        
        # actives.close()
        
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
              
      
def set_query(pendings, tipo):
    orders_ids = lambda x: [y.get("order_id") for y in x]
    
    query = ""
    verify_historical = orders_ids(filter_transactions("tipo", tipo, pendings))
    if verify_historical:
        where = "_in: %s"%(verify_historical) if len(verify_historical)>1 else f": \"{verify_historical[0]}\""
        query = """
            orderhistorysells(where: {order_id%s}) { 
                status
                signer_id
                owner_id
                order_id
            }
        """%(where)
    return query

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
    }
    """

    return requests.post("https://api.thegraph.com/subgraphs/name/hrpalencia/p2p", headers={'Content-Type': 'application/json'}, json={'query': query}).json().get("data")

def get_historical(pendings):
    query_hs = set_query(pendings, "sell")
    query_hb = set_query(pendings, "buy")
    
    query = """
    query MyQuery {
        %s
        %s
    }
    """%(query_hs, query_hb)
    return requests.post("https://api.thegraph.com/subgraphs/name/hrpalencia/p2p", headers={'Content-Type': 'application/json'}, json={'query': query.replace("'", "\"")}).json().get("data")

def verify_transactions():
    try:
        active_transactions = get_transactions()
        
        if active_transactions:
            bot = telebot.TeleBot("6683045934:AAFcupOm_6sKHt_Lk9QS3O2j8SBdJUOJHfU")
            
            list_wallet_bot = requests.post("https://nearp2p.com/wallet-p2p/walletbot/list_wallet_bot", headers = {'Content-type': 'application/json'}).json().get("data")
            
            notify_new_transaction = []
            
            add_transactions(active_transactions.get("ordersells") or [], list_wallet_bot, notify_new_transaction, "sell")
            add_transactions(active_transactions.get("orderbuys") or [], list_wallet_bot, notify_new_transaction, "buy")

            for wallets in notify_new_transaction:
                tipo = 'venta' if wallets['tipo'] == 'sell' else 'compra'
                if wallets.get("chat_owner"): bot.send_message(chat_id = wallets["chat_owner"], text = generate_msg_new(wallets.get("order_id"), wallets['wallet_owner'], tipo))
                if wallets.get("chat_signer"): bot.send_message(chat_id = wallets["chat_signer"], text = generate_msg_new(wallets.get("order_id"), wallets['wallet_signer'], tipo))
                
            pendings = get_all()
            if len(pendings) > 0: # verify_historical_sells or verify_historical_buys
                
                historical_transactions = get_historical(pendings)
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
    elif to_modify == 2:
        return f"Su orden de {tipo} N°{order_id} de la wallet {name} ha sido cancelada."
    
    return f"🥳 Felicitaciones su orden de {tipo} N°{order_id} de la wallet {name} ha finalizado con éxito."

def generate_msg_new(order_id, name, tipo):
    return f"Se ha generado la orden de {tipo} N°{order_id} de intercambio para {name} por favor verificar." 