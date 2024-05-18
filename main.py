import time
from functions import verify_transactions

def app_notifications():
    while True:
        verify_transactions()
        time.sleep(30)

if __name__ == "__main__":
    app_notifications()