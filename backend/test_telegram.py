"""
Direct test of Telegram notification without running the server.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from services.telegram_notifier import send_test_notification

# Load environment variables
load_dotenv()

print("🧪 Testing Telegram Integration...\n")

# Check configuration
bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

print(f"Bot Token: {bot_token[:20]}..." if bot_token else "❌ Bot Token not set")
print(f"Chat ID: {chat_id}\n")

if not bot_token or not chat_id:
    print("❌ Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    sys.exit(1)

# Send test notification
print("📤 Sending test notification...")
success = send_test_notification()

if success:
    print("\n✅ Success! Check your Telegram bot for the message.")
else:
    print("\n❌ Failed to send notification. Check the error above.")
