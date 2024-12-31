import os
import time
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store active users who want price updates
active_users = set()

def setup_driver(headless=True):
    """
    Sets up the Selenium WebDriver with desired options.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")  # Applicable to Windows OS only
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images for faster loading

    # Initialize WebDriver using webdriver-manager for automatic driver management
    driver = webdriver.Chrome(
        service=ChromeService(ChromeDriverManager().install()),
        options=chrome_options
    )
    return driver

def get_abc_bullion_price(driver, url):
    """
    Extracts the price from ABC Bullion website.
    """
    try:
        driver.get(url)
        # print(f"Navigated to ABC Bullion URL: {url}")

        # Wait until the price element is present
        wait = WebDriverWait(driver, 10)  # 10 seconds timeout
        price_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.scope-buy-by p.price-container span.price"))
        )

        # Extract the text from the price element
        price_text = price_element.text.strip()
        print(f"ABC Bullion Price: ${price_text}")
        return price_text

    except TimeoutException:
        print("Timeout: Price element not found on ABC Bullion page.")
        return None
    except Exception as e:
        print(f"Error fetching ABC Bullion price: {e}")
        return None

def get_aarav_bullion_prices(driver, url):
    """
    Extracts specific prices from Aarav Bullion website using JavaScript execution to avoid stale elements.
    """
    try:
        driver.get(url)
        # print(f"Navigated to Aarav Bullion URL: {url}")

        # Wait until the swiper-container is present
        wait = WebDriverWait(driver, 15)  # Increased timeout to 15 seconds
        swiper_container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.swiper-container.s1"))
        )
        # print("Swiper container found.")

        # Optional: Wait for slides to load
        time.sleep(2)  # Adjust based on network speed

        # JavaScript snippet to extract all required data in one go
        script = """
        const data = [];
        // Select all swiper-slides that contain the Trending_Table_Root
        const slides = document.querySelectorAll("div.swiper-slideTrending");

        slides.forEach(slide => {
            const table = slide.querySelector("table.Trending_Table_Root");
            if (table) {
                // Select all second_table within Trending_Table_Root
                const second_tables = table.querySelectorAll("table.second_table");
                second_tables.forEach(second_table => {
                    const rows = second_table.querySelectorAll("tr[style='text-align: center;']");
                    rows.forEach(row => {
                        const label_td = row.querySelector("td.paddingg.second_label");
                        const price_td = row.querySelector("td.paddingg:nth-child(2)");
                        const buy_td = row.querySelector("td.paddingg:nth-child(3)");  // Third <td>
                        if (label_td && price_td && buy_td) {
                            const label = label_td.innerText.trim();
                            const price = price_td.querySelector("span") ? price_td.querySelector("span").innerText.trim() : "";
                            const buy_a = buy_td.querySelector("a.btn-default");
                            const buyLink = buy_a ? buy_a.href.trim() : "";
                            data.push({ label, price, buyLink });
                        }
                    });
                });
            }
        });
        return data;
        """

        # Execute the JavaScript and retrieve the data
        prices = driver.execute_script(script)
        # print(f"Extracted {len(prices)} price entries from Aarav Bullion.")

        if not prices:
            print("No price entries found. Possible reasons:")
            print("- The structure of the website has changed.")
            print("- The data is loaded asynchronously after the script executes.")
            print("- The script needs to interact with the page (e.g., clicking on tabs) to load the data.")
            return None

        # Process and display only the first extracted data entry
        first_price = prices[0]
        label = first_price['label']
        price = first_price['price']
        buy_link = first_price['buyLink']

        print(f"\nAarav Bullion Prices: Rs.{price}")
        # print(f"{label}: {price}")

        return first_price

    except TimeoutException:
        print("Timeout: Swiper container or Trending_Table_Root not found on Aarav Bullion page.")
        return None
    except Exception as e:
        print(f"Error fetching Aarav Bullion prices: {e}")
        return None

def start(update: Update, context: CallbackContext):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    active_users.add(user_id)
    welcome_message = (
        "👋 Welcome to the Gold Price Tracker Bot!\n\n"
        "Available commands:\n"
        "/check - Get current gold prices\n"
        "/subscribe - Subscribe to price updates\n"
        "/unsubscribe - Unsubscribe from updates\n"
        "/help - Show this help message"
    )
    update.message.reply_text(welcome_message)

def help_command(update: Update, context: CallbackContext):
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 Gold Price Tracker Bot Commands:\n\n"
        "/check - Get current gold prices\n"
        "/subscribe - Get price updates every hour\n"
        "/unsubscribe - Stop receiving updates\n"
        "/help - Show this help message"
    )
    update.message.reply_text(help_text)

def check_prices(update: Update, context: CallbackContext):
    """Get current prices when /check command is issued."""
    update.message.reply_text("🔍 Checking current gold prices...")
    
    try:
        # Initialize the WebDriver
        driver = setup_driver(headless=True)
        
        try:
            # Get ABC Bullion price
            abc_price = get_abc_bullion_price(
                driver, 
                "https://www.abcbullion.com.au/store/gold/gabgtael375g-abc-bullion-tael-cast-bar"
            )
            
            # Get Aarav Bullion price
            aarav_price = get_aarav_bullion_prices(
                driver, 
                "https://aaravbullion.in/"
            )
            
            # Format message
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"📊 Gold Prices as of {current_time}\n\n"
            
            if abc_price:
                message += f"ABC Bullion: ${abc_price}\n"
            else:
                message += "ABC Bullion: Price unavailable\n"
                
            if aarav_price:
                message += f"Aarav Bullion: Rs.{aarav_price['price']}\n"
            else:
                message += "Aarav Bullion: Price unavailable\n"
            
            update.message.reply_text(message)
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error checking prices: {e}")
        update.message.reply_text("❌ Sorry, there was an error checking the prices. Please try again later.")

def subscribe(update: Update, context: CallbackContext):
    """Subscribe to price updates."""
    user_id = update.effective_user.id
    if user_id not in active_users:
        active_users.add(user_id)
        update.message.reply_text("✅ You've successfully subscribed to price updates! You'll receive updates every hour.")
    else:
        update.message.reply_text("You're already subscribed to price updates!")

def unsubscribe(update: Update, context: CallbackContext):
    """Unsubscribe from price updates."""
    user_id = update.effective_user.id
    if user_id in active_users:
        active_users.remove(user_id)
        update.message.reply_text("❌ You've been unsubscribed from price updates.")
    else:
        update.message.reply_text("You're not currently subscribed to updates!")

def send_price_updates(context: CallbackContext):
    """Send price updates to all subscribed users."""
    if not active_users:
        return
        
    try:
        driver = setup_driver(headless=True)
        
        try:
            # Get prices
            abc_price = get_abc_bullion_price(
                driver, 
                "https://www.abcbullion.com.au/store/gold/gabgtael375g-abc-bullion-tael-cast-bar"
            )
            aarav_price = get_aarav_bullion_prices(
                driver, 
                "https://aaravbullion.in/"
            )
            
            # Format message
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"🔄 Scheduled Update - {current_time}\n\n"
            
            if abc_price:
                message += f"ABC Bullion: ${abc_price}\n"
            else:
                message += "ABC Bullion: Price unavailable\n"
                
            if aarav_price:
                message += f"Aarav Bullion: Rs.{aarav_price['price']}\n"
            else:
                message += "Aarav Bullion: Price unavailable\n"
            
            # Send to all subscribed users
            bot = context.bot
            for user_id in active_users:
                try:
                    bot.send_message(chat_id=user_id, text=message)
                except Exception as e:
                    logger.error(f"Error sending update to user {user_id}: {e}")
                    
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error in scheduled update: {e}")

def main():
    """Start the bot."""
    # Get your token from environment variable
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

    # Create the Updater and pass it your bot's token
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("check", check_prices))
    dp.add_handler(CommandHandler("subscribe", subscribe))
    dp.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Add job for periodic updates (every hour)
    updater.job_queue.run_repeating(send_price_updates, interval=3600, first=10)

    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == "__main__":
    main()
