#!/usr/bin/env python3
import os
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
import pytz
from datetime import datetime
import logging
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Configure logging with timestamp
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)

# Suppress unnecessary logs
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

def setup_driver():
    """Sets up the Selenium WebDriver with Chromium options."""
    print("🔧 Setting up WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    chrome_bin = "/usr/bin/chromium-browser"
    chromedriver_path = "/usr/bin/chromedriver"
    
    try:
        service = ChromeService(executable_path=chromedriver_path)
        chrome_options.binary_location = chrome_bin
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ WebDriver setup complete")
        return driver
    except Exception as e:
        print(f"❌ WebDriver setup failed: {str(e)}")
        raise

def get_abc_bullion_price(driver):
    """Extracts the price from ABC Bullion website."""
    try:
        print("🌐 Accessing ABC Bullion website...")
        driver.get("https://www.abcbullion.com.au/store/gold/gabgtael375g-abc-bullion-tael-cast-bar")
        wait = WebDriverWait(driver, 10)
        price_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.scope-buy-by p.price-container span.price"))
        )
        price = price_element.text.strip()
        print(f"💰 ABC Bullion price found: {price}")
        return price
    except Exception as e:
        print(f"❌ Error fetching ABC Bullion price: {str(e)}")
        return "Price unavailable"

def get_aarav_bullion_price(driver):
    """Extracts prices from Aarav Bullion website."""
    try:
        print("🌐 Accessing Aarav Bullion website...")
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
        print(f"💰 Aarav Bullion price found: {price}")
        return price if price else "Price unavailable"
    except Exception as e:
        print(f"❌ Error fetching Aarav Bullion price: {str(e)}")
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
        print(f"\n❌ Error in fetch_prices: {str(e)}")
        return "Sorry, there was an error fetching the prices."
    finally:
        driver.quit()

def start(update: Update, context: CallbackContext):
    """Handle /start command."""
    user = update.effective_user
    print(f"\n👋 New user started bot: {user.id} (@{user.username})")
    update.message.reply_text(
        "👋 Welcome to the Bullion Price Bot!\n\n"
        "Commands:\n"
        "/price - Get current prices"
    )

def get_price(update: Update, context: CallbackContext):
    """Handle /price command."""
    user = update.effective_user
    print(f"\n📱 Price request from user: {user.id} (@{user.username})")
    message = update.message.reply_text("Fetching prices, please wait...")
    try:
        price_message = fetch_prices()
        print(f"\n📤 Sending price update to user: {user.id}")
        message.edit_text(price_message)
    except Exception as e:
        print(f"❌ Error in price command: {str(e)}")
        message.edit_text("Sorry, there was an error fetching the prices.")

def error_handler(update: Update, context: CallbackContext):
    """Handle errors."""
    print(f"\n❌ Error occurred: {context.error}")
    try:
        if update and update.message:
            update.message.reply_text("Sorry, something went wrong. Please try again later.")
    except:
        pass

def main():
    """Main function."""
    print("\n🎬 Starting bot...")
    
    # Validate environment variables
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        print("❌ No TELEGRAM_TOKEN found!")
        return

    # Initialize bot
    try:
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher

        # Add handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("price", get_price))
        dp.add_error_handler(error_handler)

        # Start webhook
        PORT = int(os.environ.get("PORT", "8443"))
        APP_NAME = os.environ.get("HEROKU_APP_NAME")
        
        print("🌐 Starting webhook...")
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"https://{APP_NAME}.herokuapp.com/{TOKEN}",
            drop_pending_updates=True
        )
        
        print("✅ Bot is running!")
        updater.bot.get_me()  # Test the bot token
        print(f"🤖 Bot username: @{updater.bot.username}")
        
        # Keep the bot running
        updater.idle()
        
    except Exception as e:
        print(f"❌ Critical error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
