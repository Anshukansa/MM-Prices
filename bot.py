import os
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
import pytz
from datetime import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def setup_driver():
    """Sets up the Selenium WebDriver with Chrome options for Heroku."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Check if running on Heroku
    if 'DYNO' in os.environ:
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
        driver = webdriver.Chrome(
            service=ChromeService(os.environ.get("CHROMEDRIVER_PATH")),
            options=chrome_options
        )
    else:
        # Local development setup
        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=chrome_options
        )
    return driver

# ... [Previous get_abc_bullion_price and get_aarav_bullion_price functions remain the same] ...

def error_handler(update: Update, context: CallbackContext):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update:
        update.message.reply_text("Sorry, something went wrong. Please try again later.")

def main():
    # Get the token from environment variable
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        logger.error("No TELEGRAM_TOKEN found in environment variables!")
        return

    # Create the Updater
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Add command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("price", get_price))
    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Add error handler
    dp.add_error_handler(error_handler)

    # Set up the job queue for periodic updates
    job_queue = updater.job_queue
    job_queue.run_repeating(send_price_update, interval=3600, first=0)  # Run every hour

    # Get port and app name from environment
    PORT = int(os.environ.get("PORT", "8443"))
    HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
    
    # Check if running on Heroku
    if 'DYNO' in os.environ:
        # Start webhook
        logger.info(f"Starting webhook on port {PORT}")
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"https://{HEROKU_APP_NAME}.herokuapp.com/{TOKEN}"
        )
    else:
        # Start polling (local development)
        logger.info("Starting polling")
        updater.start_polling()
    
    logger.info("Bot started")
    updater.idle()

if __name__ == "__main__":
    main()
