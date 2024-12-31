import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging
import telegram
from datetime import datetime

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# List of subscriber IDs (replace with your actual subscriber IDs)
SUBSCRIBERS = {
    7932502148 # Example user ID - replace with real ones
}

def setup_driver():
    """Sets up the Selenium WebDriver with headless Chrome."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # For Heroku
    chrome_binary_path = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
    
    options.binary_location = chrome_binary_path
    service = Service(executable_path=chromedriver_path)
    
    return webdriver.Chrome(service=service, options=options)

def format_url(model, storage):
    base_model = "-".join(model.split("-")[:2])
    return f"https://mobilemonster.com.au/sell-your-phone/apple/mobiles/{base_model}/{model}-{storage}"

def fetch_prices_for_two_models(driver, models_pair, storages):
    prices = []
    tabs = []

    # Open tabs for both models and all storages
    for model in models_pair:
        for storage in storages:
            url = format_url(model, storage)
            logging.info(f"Opening URL: {url}")
            driver.execute_script(f"window.open('{url}', '_blank');")
            tabs.append((driver.window_handles[-1], model, storage, url))

    # Fetch prices from open tabs
    for tab, model, storage, url in tabs:
        driver.switch_to.window(tab)
        try:
            if "Page Not Found" in driver.page_source or "404" in driver.title:
                price = "N/A"
            else:
                reduced_price_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//label/div[contains(text(), 'I will accept the reduced price of')]")
                    )
                )
                price_text = reduced_price_element.text
                if "AU$" in price_text:
                    price = price_text.split("AU$")[-1].split()[0].replace(',', '')
                else:
                    price = "N/A"
            logging.info(f"Price for {model} ({storage}): {price}")
        except Exception as e:
            logging.error(f"Error fetching price for {model} ({storage}): {e}")
            price = "N/A"

        prices.append((model, storage, price))
        driver.close()

    driver.switch_to.window(driver.window_handles[0])
    return prices

def format_message(results):
    """Formats the results into a readable message."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"📱 iPhone Prices (as of {current_time})\n\n"
    
    # Add header row
    header = "Model".ljust(20)
    for storage in ["64GB", "128GB", "256GB", "512GB", "1TB"]:
        header += f"| {storage.ljust(8)}"
    message += f"`{header}`\n"
    
    # Add separator
    message += "`" + "-" * 20 + ("|" + "-" * 9) * 5 + "`\n"
    
    # Add data rows
    for model in results["Model"]:
        row = model.ljust(20)
        for storage in ["64GB", "128GB", "256GB", "512GB", "1TB"]:
            idx = results["Model"].index(model)
            price = results[storage][idx] if idx < len(results[storage]) else "N/A"
            if price and price != "N/A":
                price = f"${price}"
            row += f"| {str(price).ljust(8)}"
        message += f"`{row}`\n"
    
    return message

def send_update():
    """Main function to fetch prices and send updates."""
    # Get Telegram token
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")

    # Initialize bot
    bot = telegram.Bot(token=token)
    
    if not SUBSCRIBERS:
        logging.info("No subscribers in the list!")
        return

    # List of models and storage options
    models = [
        "iphone-11", "iphone-11-pro", "iphone-11-pro-max",
        "iphone-12", "iphone-12-mini", "iphone-12-pro", "iphone-12-pro-max",
        "iphone-13", "iphone-13-mini", "iphone-13-pro", "iphone-13-pro-max",
        "iphone-14", "iphone-14-plus", "iphone-14-pro", "iphone-14-pro-max"
    ]
    storages = ["64gb", "128gb", "256gb", "512gb", "1tb"]

    # Initialize results dictionary
    results = {storage.upper(): [] for storage in storages}
    results["Model"] = []

    # Initialize WebDriver
    driver = setup_driver()
    
    try:
        # Process models in pairs
        for i in range(0, len(models), 2):
            models_pair = models[i:i + 2]
            logging.info(f"Processing models: {models_pair}")
            fetched_data = fetch_prices_for_two_models(driver, models_pair, storages)

            # Organize results
            for model, storage, price in fetched_data:
                formatted_model = model.replace("-", " ").title()
                if formatted_model not in results["Model"]:
                    results["Model"].append(formatted_model)
                col_name = storage.upper()
                while len(results[col_name]) < len(results["Model"]) - 1:
                    results[col_name].append("")
                results[col_name].append(price)

        # Ensure all columns align
        max_rows = max(len(results[col]) for col in results)
        for col in results:
            while len(results[col]) < max_rows:
                results[col].append("")

        # Format message and send to subscribers
        message = format_message(results)
        
        # Split message if too long
        max_length = 4096
        messages = [message[i:i+max_length] for i in range(0, len(message), max_length)]
        
        for user_id in SUBSCRIBERS:
            try:
                for msg in messages:
                    bot.send_message(
                        chat_id=user_id,
                        text=msg,
                        parse_mode='Markdown'
                    )
                logging.info(f"Price matrix sent to user {user_id}")
            except Exception as e:
                logging.error(f"Failed to send message to user {user_id}: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    logging.info("Starting price update script...")
    send_update()
    logging.info("Price update script completed.")
