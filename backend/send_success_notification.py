import requests
import os
from dotenv import load_dotenv

load_dotenv()

message = """Pipeline Test Complete!

Transcription: SUCCESS
Language: Russian
Duration: 1 min
Text: 873 chars

Analysis: 2 clips found
High-Quality: 1 clip (score >= 8)

File ID: 645a3ffa-e633-4e19-8472-b0cb5ba4d99c

Next: Render + Upload to YouTube

Autonomous Factory is READY!
"""

bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
payload = {
    'chat_id': chat_id,
    'text': message
}

r = requests.post(url, json=payload)
print('Sent!' if r.json().get('ok') else r.json())
