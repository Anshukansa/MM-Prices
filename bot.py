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
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Suppress unnecessary logging
logging.getLogger('telegram').setLevel(logging.INFO)
logging.getLogger('asyncio').setLevel(logging.WARNING)

def setup_driver():
    """Sets up the Selenium WebDriver with Chromium options for Heroku-24."""
    print("🔧 Setting up WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-setuid-sandbox')
    chrome_options.add_argument('--single-process')
    
    browser_path = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/chromium-browser")
    driver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    
    print(f"📦 Browser Path: {browser_path}")
    print(f"📦 Driver Path: {driver_path}")
    
    try:
        service = ChromeService(executable_path=driver_path)
        chrome_options.binary_location = browser_path
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ WebDriver setup complete")
        return driver
    except Exception as e:
        print(f"❌ WebDriver setup failed: {e}")
        raise

def get_abc_bullion_price(driver):
    """Extracts the price from ABC Bullion website."""
    try:
        print("🌐 Accessing ABC Bullion website...")
        driver.get("https://www.abcbullion.com.au/store/gold/gabgtael375g-abc-bullion-tael-cast-bar")
        print("📍 Waiting for ABC Bullion price element...")
        wait = WebDriverWait(driver, 10)
        price_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.scope-buy-by p.price-container span.price"))
        )
        price = price_element.text.strip()
        print(f"💰 ABC Bullion price found: {price}")
        return price
    except Exception as e:
        print(f"❌ Error fetching ABC Bullion price: {e}")
        logger.error(f"Error fetching ABC Bullion price: {e}")
        return "Price unavailable"

def get_aarav_bullion_price(driver):
    """Extracts prices from Aarav Bullion website."""
    try:
        print("🌐 Accessing Aarav Bullion website...")
        driver.get("https://aaravbullion.in/")
        print("📍 Waiting for Aarav Bullion container...")
        wait = WebDriverWait(driver, 15)
        swiper_container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.swiper-container.s1"))
        )
        print("✅ Swiper container found")
        
        script = """
        const data = [];
        const slides = document.querySelectorAll("div.swiper-slideTrending");
        console.log('Found slides:', slides.length);
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
        print(f"💰 Aarav Bullion price found: {price}")
        return price if price else "Price unavailable"
    except Exception as e:
        print(f"❌ Error fetching Aarav Bullion price: {e}")
        logger.error(f"Error fetching Aarav Bullion price: {e}")
        return "Price unavailable"

def fetch_prices():
    """Fetches prices from both sources and returns formatted message."""
    print("\n🚀 Starting price fetch operation...")
    driver = setup_driver()
    try:
        abc_price = get_abc_bullion_price(driver)
        aarav_price = get_aarav_bullion_price(driver)
        
        ist = pytz.timezone('Asia/Kolkata')
        current_time = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S %Z')
        
        message = f"🕒 Price Update ({current_time})\n\n"
        message += f"🏆 ABC Bullion: ${abc_price}\n"
        message += f"💫 Aarav Bullion: ₹{aarav_price}"
        
        print("\n✅ Price fetch complete!")
        return message
    except Exception as e:
        error_msg = f"Error in fetch_prices: {e}"
        print(f"\n❌ {error_msg}")
        logger.error(error_msg)
        return "Sorry, there was an error fetching the prices."
    finally:
        print("\n🔄 Closing WebDriver...")
        driver.quit()

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
    message = update.message.reply_text("Fetching prices, please wait...")
    try:
        price_message = fetch_prices()
        print(f"\n📤 Sending price update to user: {user_id}")
        message.edit_text(price_message)
    except Exception as e:
        print(f"❌ Error in price command: {e}")
        message.edit_text("Sorry, there was an error fetching the prices.")

def error_handler(update: Update, context: CallbackContext):
    """Log Errors caused by Updates."""
    print(f"\n❌ Error occurred: {context.error}")
    logger.error(f'Update "{update}" caused error "{context.error}"')
    try:
        if update and update.message:
            update.message.reply_text("Sorry, something went wrong. Please try again later.")
    except:
        pass

def main():
    print("\n🤖 Starting bot initialization...")
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        print("❌ No TELEGRAM_TOKEN found!")
        return

    print("🔑 Creating updater...")
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
        webhook_url=f"https://{HEROKU_APP_NAME}.herokuapp.com/{TOKEN}",
        drop_pending_updates=True
    )
    
    print("\n✅ Bot successfully started!")
    print(f"🤖 Bot username: @{updater.bot.get_me().username}")
    updater.idle()

if __name__ == "__main__":
    print("\n🎬 Starting bot script...")
    main()
