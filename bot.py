import os
import time
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import telegram

# Flask app initialization
app = Flask(__name__)

# Store prices globally
prices = {}
last_updated = None

# List of subscriber IDs (replace with your actual subscriber IDs)
SUBSCRIBERS = {
    7932502148  # Example user ID - replace with real ones
}

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def setup_driver():
    """Sets up the Selenium WebDriver with headless Chrome."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    chrome_binary_path = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
    
    options.binary_location = chrome_binary_path
    service = Service(executable_path=chromedriver_path)
    
    return webdriver.Chrome(service=service, options=options)

def format_url(model, storage):
    base_model = "-".join(model.split("-")[:2])
    return f"https://mobilemonster.com.au/sell-your-phone/apple/mobiles/{base_model}/{model}-{storage}"

def fetch_prices_for_models(driver, models, storages):
    """Fetch prices for multiple models and storages."""
    prices_data = {storage.upper(): [] for storage in storages}
    prices_data["Model"] = []

    for model in models:
        for storage in storages:
            url = format_url(model, storage)
            logging.info(f"Opening URL: {url}")
            driver.get(url)

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
            except Exception as e:
                logging.error(f"Error fetching price for {model} ({storage}): {e}")
                price = "N/A"

            # Add fetched price to the data structure
            prices_data["Model"].append(model.replace("-", " ").title())
            prices_data[storage.upper()].append(price)

    return prices_data

def send_update():
    """Main function to fetch prices and send updates via Telegram."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")

    bot = telegram.Bot(token=token)

    if not SUBSCRIBERS:
        logging.info("No subscribers in the list!")
        return

    models = [
        "iphone-11", "iphone-11-pro", "iphone-11-pro-max",
        "iphone-12", "iphone-12-mini", "iphone-12-pro", "iphone-12-pro-max",
        "iphone-13", "iphone-13-mini", "iphone-13-pro", "iphone-13-pro-max",
        "iphone-14", "iphone-14-plus", "iphone-14-pro", "iphone-14-pro-max"
    ]
    storages = ["64gb", "128gb", "256gb", "512gb", "1tb"]

    # Set up WebDriver
    driver = setup_driver()

    try:
        # Fetch prices for all models
        results = fetch_prices_for_models(driver, models, storages)

        # Format messages by series (this is optional but keeps the format tidy)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        messages = format_message_by_series(results, current_time)

        # Send messages to subscribers
        for user_id in SUBSCRIBERS:
            try:
                for msg in messages:
                    bot.send_message(
                        chat_id=user_id,
                        text=msg,
                        parse_mode='Markdown'
                    )
                    logging.info(f"Message part sent to user {user_id}")
            except Exception as e:
                logging.error(f"Failed to send message to user {user_id}: {e}")

    finally:
        driver.quit()

def format_message_by_series(results, current_time):
    """Formats the results into a series of messages grouped by iPhone series."""
    messages = []

    # Header message
    header_msg = (
        f"📱 *iPhone Price Update*\n"
        f"🕒 {current_time}\n"
        f"🏪 MobileMonster.com.au\n"
        f"{'='*32}\n\n"
    )
    messages.append(header_msg)

    # Create a message for each model in results
    for model, price_list in zip(results["Model"], zip(*[results[storage] for storage in results if storage != "Model"])):
        model_msg = f"📱 *{model}*\n"
        for storage, price in zip(results.keys(), price_list):
            if storage != "Model":
                model_msg += f"  • {storage}: {format_price(price)}\n"
        messages.append(model_msg)

    # Add footer message
    footer_msg = (
        f"{'='*32}\n"
        "💡 *Legend*:\n"
        "💰 = Available Price\n"
        "❌ = Not Available\n\n"
        "📊 _Prices updated every hour_"
    )
    messages.append(footer_msg)
    
    return messages

def format_price(price):
    """Formats the price with appropriate symbol and color emoji."""
    if price == "N/A":
        return "❌"
    try:
        price_val = float(price)
        return f"💰${price}:"
    except:
        return "❌"

@app.before_first_request
def fetch_initial_prices():
    """Fetch prices when the app starts."""
    global prices, last_updated
    models = [
        "iphone-11", "iphone-11-pro", "iphone-11-pro-max",
        "iphone-12", "iphone-12-mini", "iphone-12-pro", "iphone-12-pro-max",
        "iphone-13", "iphone-13-mini", "iphone-13-pro", "iphone-13-pro-max",
        "iphone-14", "iphone-14-plus", "iphone-14-pro", "iphone-14-pro-max"
    ]
    storages = ["64gb", "128gb", "256gb", "512gb", "1tb"]
    
    # Set up WebDriver
    driver = setup_driver()

    try:
        # Fetch prices for all models
        prices = fetch_prices_for_models(driver, models, storages)
        last_updated = time.time()

    finally:
        driver.quit()

@app.route('/')
def index():
    """Render the main page with the latest prices."""
    global prices, last_updated
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template('index.html', prices=prices, last_updated=last_updated, current_time=current_time)

@app.route('/refresh_prices')
def refresh_prices():
    """Handles refreshing the prices."""
    global prices, last_updated

    if (time.time() - last_updated) > 3600:
        prices = fetch_prices_for_models(setup_driver(), [
            "iphone-11", "iphone-11-pro", "iphone-11-pro-max",
            "iphone-12", "iphone-12-mini", "iphone-12-pro", "iphone-12-pro-max",
            "iphone-13", "iphone-13-mini", "iphone-13-pro", "iphone-13-pro-max",
            "iphone-14", "iphone-14-plus", "iphone-14-pro", "iphone-14-pro-max"
        ], ["64gb", "128gb", "256gb", "512gb", "1tb"])
        last_updated = time.time()
        return redirect(url_for('index'))
    else:
        return jsonify({"message": "Prices can only be refreshed once per hour."})

if __name__ == '__main__':
    logging.info("Starting the Flask app...")
    app.run(debug=True)
