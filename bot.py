import os
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
import pytz
from datetime import datetime
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_driver():
    """Sets up the Selenium WebDriver with Chrome options for Heroku."""
    print("🔧 Setting up WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    print("📦 Setting up Chrome for Heroku...")
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    driver = webdriver.Chrome(
        service=ChromeService(os.environ.get("CHROMEDRIVER_PATH")),
        options=chrome_options
    )
    print("✅ WebDriver setup complete")
    return driver

# [Previous functions get_abc_bullion_price, get_aarav_bullion_price, and fetch_prices remain the same]

def start(update: Update, context: CallbackContext):
    """Handles the /start command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    print(f"\n👋 New user started bot: {user_id} (@{username})")
    update.message.reply_text(
        "👋 Welcome to the Bullion Price Bot!\n\n"
        "Commands:\n"
        "/price - Get current prices"
    )

def get_price(update: Update, context: CallbackContext):
    """Handles the /price command."""
    user_id = update.effective_user.id
    username = update.effective_user.username
    print(f"\n📱 Price request from user: {user_id} (@{username})")
    update.message.reply_text("Fetching prices, please wait...")
    price_message = fetch_prices()
    print(f"\n📤 Sending price update to user: {user_id}")
    update.message.reply_text(price_message)

def error_handler(update: Update, context: CallbackContext):
    """Log Errors caused by Updates."""
    print(f"\n❌ Error occurred: {context.error}")
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update:
        update.message.reply_text("Sorry, something went wrong. Please try again later.")

def main():
    print("\n🤖 Starting bot initialization...")
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        print("❌ No TELEGRAM_TOKEN found!")
        return

    print("🔑 Token found, creating updater...")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    print("📝 Adding command handlers...")
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("price", get_price))
    dp.add_error_handler(error_handler)

    PORT = int(os.environ.get("PORT", "8443"))
    HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
    
    print(f"\n🌐 Starting webhook on port {PORT}")
    updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"https://{HEROKU_APP_NAME}.herokuapp.com/{TOKEN}"
    )
    
    print("\n✅ Bot successfully started!")
    updater.idle()

if __name__ == "__main__":
    print("\n🎬 Starting bot script...")
    main()
