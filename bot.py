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

def get_abc_bullion_price(driver):
    """Extracts the price from ABC Bullion website."""
    try:
        driver.get("https://www.abcbullion.com.au/store/gold/gabgtael375g-abc-bullion-tael-cast-bar")
        wait = WebDriverWait(driver, 10)
        price_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.scope-buy-by p.price-container span.price"))
        )
        return price_element.text.strip()
    except Exception as e:
        logger.error(f"Error fetching ABC Bullion price: {e}")
        return "Price unavailable"

def get_aarav_bullion_price(driver):
    """Extracts prices from Aarav Bullion website."""
    try:
        driver.get("https://aaravbullion.in/")
        wait = WebDriverWait(driver, 15)
        swiper_container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.swiper-container.s1"))
        )
        
        script = """
        const data = [];
        const slides = document.querySelectorAll("div.swiper-slideTrending");
        slides.forEach(slide => {
            const table = slide.querySelector("table.Trending_Table_Root");
            if (table) {
                const second_tables = table.querySelectorAll("table.second_table");
                second_tables.forEach(second_table => {
                    const rows = second_table.querySelectorAll("tr[style='text-align: center;']");
                    rows.forEach(row => {
                        const label_td = row.querySelector("td.paddingg.second_label");
                        const price_td = row.querySelector("td.paddingg:nth-child(2)");
                        if (label_td && price_td) {
                            const price = price_td.querySelector("span") ? price_td.querySelector("span").innerText.trim() : "";
                            data.push(price);
                        }
                    });
                });
            }
        });
        return data[0];
        """
        price = driver.execute_script(script)
        return price if price else "Price unavailable"
    except Exception as e:
        logger.error(f"Error fetching Aarav Bullion price: {e}")
        return "Price unavailable"

def fetch_prices():
    """Fetches prices from both sources and returns formatted message."""
    driver = setup_driver()
    try:
        abc_price = get_abc_bullion_price(driver)
        aarav_price = get_aarav_bullion_price(driver)
        
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S %Z')
        
        message = f"🕒 Price Update ({current_time})\n\n"
        message += f"🏆 ABC Bullion: ${abc_price}\n"
        message += f"💫 Aarav Bullion: ₹{aarav_price}"
        
        return message
    except Exception as e:
        logger.error(f"Error in fetch_prices: {e}")
        return "Sorry, there was an error fetching the prices."
    finally:
        driver.quit()

def start(update: Update, context: CallbackContext):
    """Handles the /start command."""
    update.message.reply_text(
        "👋 Welcome to the Bullion Price Bot!\n\n"
        "Commands:\n"
        "/price - Get current prices"
    )

def get_price(update: Update, context: CallbackContext):
    """Handles the /price command."""
    update.message.reply_text("Fetching prices, please wait...")
    price_message = fetch_prices()
    update.message.reply_text(price_message)

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

    # Add error handler
    dp.add_error_handler(error_handler)

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
