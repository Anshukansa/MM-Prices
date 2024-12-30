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

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Changed to DEBUG for more detailed logs
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
    
    chrome_bin = os.environ.get("GOOGLE_CHROME_BIN")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    
    print(f"📦 Chrome Binary Path: {chrome_bin}")
    print(f"📦 ChromeDriver Path: {chromedriver_path}")
    
    chrome_options.binary_location = chrome_bin
    
    try:
        driver = webdriver.Chrome(
            service=ChromeService(chromedriver_path),
            options=chrome_options
        )
        print("✅ WebDriver setup complete")
        return driver
    except Exception as e:
        print(f"❌ WebDriver setup failed: {e}")
        raise

# [Previous price fetching functions remain the same]

def start(update: Update, context: CallbackContext):
    """Handles the /start command."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username
        print(f"\n👋 New user started bot: {user_id} (@{username})")
        update.message.reply_text(
            "👋 Welcome to the Bullion Price Bot!\n\n"
            "Commands:\n"
            "/price - Get current prices"
        )
    except Exception as e:
        print(f"❌ Error in start command: {e}")
        logger.error(f"Start command error: {e}")

def get_price(update: Update, context: CallbackContext):
    """Handles the /price command."""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username
        print(f"\n📱 Price request from user: {user_id} (@{username})")
        message = update.message.reply_text("Fetching prices, please wait...")
        price_message = fetch_prices()
        print(f"\n📤 Sending price update to user: {user_id}")
        message.edit_text(price_message)
    except Exception as e:
        print(f"❌ Error in price command: {e}")
        logger.error(f"Price command error: {e}")
        update.message.reply_text("Sorry, there was an error fetching the prices.")

def error_handler(update: Update, context: CallbackContext):
    """Log Errors caused by Updates."""
    print(f"\n❌ Error occurred: {context.error}")
    logger.error(f'Update "{update}" caused error "{context.error}"')
    try:
        if update:
            update.message.reply_text("Sorry, something went wrong. Please try again later.")
    except:
        pass

def main():
    try:
        print("\n🤖 Starting bot initialization...")
        
        # Validate environment variables
        TOKEN = os.environ.get("TELEGRAM_TOKEN")
        if not TOKEN:
            raise ValueError("No TELEGRAM_TOKEN found in environment!")
            
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
        if not HEROKU_APP_NAME:
            raise ValueError("No HEROKU_APP_NAME found in environment!")
        
        print("🔑 Creating updater...")
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher

        print("📝 Adding command handlers...")
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("price", get_price))
        dp.add_error_handler(error_handler)

        # Get port from environment
        PORT = int(os.environ.get("PORT", "8443"))
        
        # Construct webhook URL
        WEBHOOK_URL = f"https://{HEROKU_APP_NAME}.herokuapp.com/{TOKEN}"
        print(f"🔗 Webhook URL: {WEBHOOK_URL}")
        
        # Start webhook
        print(f"\n🌐 Starting webhook on port {PORT}")
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=WEBHOOK_URL,
            drop_pending_updates=True  # Ignore messages sent while bot was offline
        )
        
        print("\n✅ Bot successfully started!")
        print(f"🤖 Bot username: @{updater.bot.get_me().username}")
        
        updater.idle()
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        logger.critical(f"Bot initialization failed: {e}")
        raise

if __name__ == "__main__":
    print("\n🎬 Starting bot script...")
    main()
