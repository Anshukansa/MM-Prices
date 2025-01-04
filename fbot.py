import os
import time
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, redirect, url_for
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Flask app initialization
app = Flask(__name__)

# Store prices globally
prices = {}
last_updated = None

# List of subscriber IDs (replace with actual ones)
SUBSCRIBERS = {
    7932502148  # Example user ID - replace with real ones
}

# Set up logging
logging.basicConfig(level=logging.INFO)

def setup_driver():
    """Sets up the Selenium WebDriver with headless Chrome."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    chrome_binary_path = os.environ.get("GOOGLE_CHROME_BIN")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    options.binary_location = chrome_binary_path
    service = Service(executable_path=chromedriver_path)
    return webdriver.Chrome(service=service, options=options)

def fetch_prices():
    """Fetches prices for models from the website."""
    models = [
        "iphone-11", "iphone-11-pro", "iphone-11-pro-max",
        "iphone-12", "iphone-12-mini", "iphone-12-pro", "iphone-12-pro-max",
        "iphone-13", "iphone-13-mini", "iphone-13-pro", "iphone-13-pro-max",
        "iphone-14", "iphone-14-plus", "iphone-14-pro", "iphone-14-pro-max"
    ]
    storages = ["64gb", "128gb", "256gb", "512gb", "1tb"]
    driver = setup_driver()
    
    prices_data = {storage.upper(): [] for storage in storages}
    prices_data["Model"] = []
    
    try:
        for model in models:
            for storage in storages:
                url = format_url(model, storage)
                logging.info(f"Opening URL: {url}")
                driver.get(url)
                try:
                    reduced_price_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, "//label/div[contains(text(), 'I will accept the reduced price of')]")
                        )
                    )
                    price_text = reduced_price_element.text
                    price = "N/A"
                    if "AU$" in price_text:
                        price = price_text.split("AU$")[-1].split()[0].replace(',', '')
                    prices_data["Model"].append(model.replace("-", " ").title())
                    prices_data[storage.upper()].append(price)
                    logging.info(f"Fetched price for {model} ({storage}): {price}")
                except Exception as e:
                    logging.error(f"Error fetching price for {model} ({storage}): {e}")
                    prices_data[storage.upper()].append("N/A")
        logging.info(f"Fetched all prices: {prices_data}")
        return prices_data
    finally:
        driver.quit()

def format_url(model, storage):
    base_model = "-".join(model.split("-")[:2])
    return f"https://mobilemonster.com.au/sell-your-phone/apple/mobiles/{base_model}/{model}-{storage}"

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
    
    logging.info("Refresh prices button clicked.")
    
    # Only update if the last refresh was more than 1 hour ago
    if last_updated is None or (time.time() - last_updated) > 3600:
        prices = fetch_prices()
        last_updated = time.time()
        logging.info("Prices updated.")
        return redirect(url_for('index'))
    else:
        logging.info("Prices refresh attempted too soon.")
        return jsonify({"message": "Prices can only be refreshed once per hour."})

if __name__ == '__main__':
    app.run(debug=True)
