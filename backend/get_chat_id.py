"""
Simple script to get your Telegram Chat ID.
Run this after sending /start to your bot.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

# Get updates from bot
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"

try:
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    if not data.get('ok'):
        print(f"❌ API Error: {data}")
        exit(1)
    
    updates = data.get('result', [])
    
    if not updates:
        print("⚠️  No messages found!")
        print("📱 Please send /start to your bot first: https://t.me/ClipsGoldBot")
        exit(0)
    
    print("✅ Found chat messages:\n")
    
    seen_chats = set()
    for update in updates:
        message = update.get('message', {})
        chat = message.get('chat', {})
        chat_id = chat.get('id')
        username = chat.get('username', 'N/A')
        first_name = chat.get('first_name', 'N/A')
        
        if chat_id and chat_id not in seen_chats:
            seen_chats.add(chat_id)
            print(f"👤 User: {first_name} (@{username})")
            print(f"🆔 Chat ID: {chat_id}")
            print(f"💬 Last message: {message.get('text', 'N/A')}")
            print("-" * 50)
    
    if seen_chats:
        print(f"\n✅ Copy one of the Chat IDs above to your .env file:")
        print(f"   TELEGRAM_CHAT_ID={list(seen_chats)[0]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
