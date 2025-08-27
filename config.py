# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
JIKAN_API = "https://api.jikan.moe/v4"

# Langues supportées
SUPPORTED_LANGUAGES = {
    'fr': 'Français'
}

# Langue par défaut
DEFAULT_LANGUAGE = 'fr'
