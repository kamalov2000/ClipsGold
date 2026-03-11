"""
Simple Telegram test without complex dependencies.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

print("Testing Telegram Integration...\n")
print(f"Bot Token: {BOT_TOKEN[:20]}..." if BOT_TOKEN else "Bot Token not set")
print(f"Chat ID: {CHAT_ID}\n")

if not BOT_TOKEN or not CHAT_ID:
    print("ERROR: Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    exit(1)

# Send test message
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

message = """
*Test Notification*

Telegram integration is working!

Your ClipsGold AI Factory is ready to send notifications.
"""

payload = {
    'chat_id': CHAT_ID,
    'text': message,
    'parse_mode': 'Markdown',
}

print("Sending test notification...")

try:
    response = requests.post(url, json=payload, timeout=10)
    response.raise_for_status()
    
    if response.json().get('ok'):
        print("\nSUCCESS! Check your Telegram (@ClipsGoldBot) for the message.")
    else:
        print(f"\nAPI Error: {response.json()}")
except Exception as e:
    print(f"\nFailed: {e}")
