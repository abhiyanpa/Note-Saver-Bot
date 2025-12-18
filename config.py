import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
DATABASE_FILE = os.getenv('DATABASE_FILE', 'notes.db')  # Default to notes.db

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in .env file")