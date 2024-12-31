import os
import time
from datetime import datetime
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import telegram

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# List of subscriber IDs (replace with your actual subscriber IDs)
SUBSCRIBERS = {
    7932502148
}

def setup_driver():
    """Sets up the Selenium WebDriver with headless Chrome."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Get Chrome paths from environment variables
    chrome_binary_path = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
    
    chrome_options.binary_location = chrome_binary_path
    service = Service(executable_path=chromedriver_path)
    
    return webdriver.Chrome(service=service, options=chrome_options)

def get_prices():
    """Gets prices from both websites."""
    driver = setup_driver()
    try:
        # ABC Bullion
        try:
            driver.get("https://www.abcbullion.com.au/store/gold/gabgtael375g-abc-bullion-tael-cast-bar")
            wait = WebDriverWait(driver, 30)
            price_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.scope-buy-by p.price-container span.price"))
            )
            abc_price = price_element.text.strip()
            logger.info(f"ABC Bullion price: {abc_price}")
        except Exception as e:
            logger.error(f"Error getting ABC price: {e}")
            abc_price = None

        # Aarav Bullion
        try:
            driver.get("https://aaravbullion.in/")
            wait = WebDriverWait(driver, 15)
            swiper = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.swiper-container.s1"))
            )
            time.sleep(2)
            
            script = """
            const data = [];
            document.querySelectorAll("div.swiper-slideTrending table.Trending_Table_Root table.second_table tr").forEach(row => {
                const price = row.querySelector("td:nth-child(2) span")?.innerText.trim();
                if (price) data.push(price);
            });
            return data[0];
            """
            aarav_price = driver.execute_script(script)
            logger.info(f"Aarav Bullion price: {aarav_price}")
        except Exception as e:
            logger.error(f"Error getting Aarav price: {e}")
            aarav_price = None

        return abc_price, aarav_price
    
    finally:
        driver.quit()

def send_updates():
    """Main function to send price updates to all subscribers."""
    # Get Telegram token
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")

    # Initialize bot
    bot = telegram.Bot(token=token)
    
    if not SUBSCRIBERS:
        logger.info("No subscribers in the list!")
        return

    # Get prices
    abc_price, aarav_price = get_prices()
    
    # Create message
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"📊 Gold Prices as of {current_time}\n\n"
    
    if abc_price:
        message += f"ABC Bullion: ${abc_price}\n"
    else:
        message += "ABC Bullion: Price unavailable\n"
        
    if aarav_price:
        message += f"Aarav Bullion: Rs.{aarav_price}\n"
    else:
        message += "Aarav Bullion: Price unavailable\n"

    # Send to all subscribers
    for user_id in SUBSCRIBERS:
        try:
            bot.send_message(chat_id=user_id, text=message)
            logger.info(f"Message sent to user {user_id}")
            time.sleep(1)  # Avoid hitting rate limits
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")

if __name__ == "__main__":
    logger.info("Starting price update script...")
    send_updates()
    logger.info("Price update script completed.")
