import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for
import telegram
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from threading import Lock

app = Flask(__name__)

# Configuration for price update
LAST_UPDATED = None  # To store the last update timestamp
PRICES = {}  # To store the prices
LOCK = Lock()  # To ensure thread safety for price updates

# Subscriber list for Telegram notifications
SUBSCRIBERS = {
    7932502148  # Example user ID, replace with real ones
}

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Fetch prices from the website
def fetch_prices():
    # This function is similar to your existing price fetching logic,
    # but now it will update the global PRICES variable
    global PRICES, LAST_UPDATED
    with LOCK:
        # Simulate fetching data and updating the global PRICES dictionary
        models = [
            "iphone-11", "iphone-11-pro", "iphone-11-pro-max",
            "iphone-12", "iphone-12-mini", "iphone-12-pro", "iphone-12-pro-max",
            "iphone-13", "iphone-13-mini", "iphone-13-pro", "iphone-13-pro-max",
            "iphone-14", "iphone-14-plus", "iphone-14-pro", "iphone-14-pro-max"
        ]
        storages = ["64gb", "128gb", "256gb", "512gb", "1tb"]
        
        # Mock prices for demonstration
        prices = {model: {storage: f"${(i+1) * 100}" for storage in storages} for i, model in enumerate(models)}

        # Update global prices and timestamp
        PRICES = prices
        LAST_UPDATED = datetime.now()
        logging.info("Prices updated successfully")

# Flask route to display the prices
@app.route('/')
def index():
    return render_template('index.html', prices=PRICES, last_updated=LAST_UPDATED)

# Flask route to handle the price refresh button
@app.route('/refresh')
def refresh_prices():
    global LAST_UPDATED

    # Check if an hour has passed since the last update
    if LAST_UPDATED and datetime.now() - LAST_UPDATED < timedelta(hours=1):
        logging.info("Price refresh attempted too soon")
        return redirect(url_for('index'))  # Redirect back to the main page without updating

    # Fetch new prices if it's time to update
    fetch_prices()

    # Notify subscribers via Telegram (optional)
    send_telegram_update()

    return redirect(url_for('index'))

# Function to send Telegram notifications
def send_telegram_update():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set!")
    bot = telegram.Bot(token=token)

    # Sending the message to all subscribers
    for user_id in SUBSCRIBERS:
        try:
            bot.send_message(chat_id=user_id, text="The prices have been updated!")
            logging.info(f"Sent update to user {user_id}")
        except Exception as e:
            logging.error(f"Failed to send message to user {user_id}: {e}")

# Run the Flask app
if __name__ == "__main__":
    logging.info("Starting Flask app...")
    fetch_prices()  # Initial fetch of prices
    app.run(host='0.0.0.0', port=5000)
