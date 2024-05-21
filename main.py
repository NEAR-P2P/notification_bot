import time
from functions import verify_transactions

def app_notifications():
    while True:
        verify_transactions()
        time.sleep(20)

if __name__ == "__main__":
    app_notifications()