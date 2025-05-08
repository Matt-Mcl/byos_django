import os
import requests
from dotenv import load_dotenv

load_dotenv()

response = requests.get("https://trmnl.matt.beer/api/v1/battery").json()

print(response)

if response["status"] != 200:
    exit(1)

voltage = response["voltage"]

url = f"https://api.telegram.org/{os.environ.get('TELEGRAM_BOT_TOKEN')}/sendMessage?chat_id={os.environ.get('TELEGRAM_CHAT_ID')}&text=TRMNL Battery voltage: {voltage}"

response = requests.get(url)
