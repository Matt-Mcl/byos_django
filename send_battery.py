import os
import requests
from dotenv import load_dotenv

load_dotenv()

response = requests.get ("http://192.168.0.63:8000/api/v1/battery").json()

if response["status"] != 200:
    exit(1)

voltage = response["voltage"]

url = f"https://api.telegram.org/{os.environ.get('TELEGRAM_BOT_TOKEN')}/sendMessage?chat_id={os.environ.get('TELEGRAM_CHAT_ID')}&text=TRMNL Battery voltage: {voltage}"

response = requests.get(url)
