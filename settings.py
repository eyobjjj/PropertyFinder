import os
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

# Google Sheets API
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

USE_SCRAPER_API = False

# Proxy settings
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")
