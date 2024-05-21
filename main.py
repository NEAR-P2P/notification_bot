import asyncio
from functions import verify_transactions

async def app_notifications():
    while True:
        try:
            await verify_transactions()
        except Exception as e:
            print(f"An error occurred: {e}")
            await asyncio.sleep(2)  # wait for 1 second before retrying

if __name__ == "__main__":
    asyncio.run(app_notifications())