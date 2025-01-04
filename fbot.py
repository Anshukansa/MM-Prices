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
    chrome_binary_path = os.environ.get("GOOGLE_CHROME_BIN", "/usr/bin/google-chrome")
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/usr/local/bin/chromedriver")
    options.binary_location = chrome_binary_path
    service = Service(executable_path=chromedriver_path)
    return webdriver.Chrome(service=service, options=options)

def format_url(model, storage):
    """Formats the URL for the model and storage combination."""
    base_model = "-".join(model.split("-")[:2])
    return f"https://mobilemonster.com.au/sell-your-phone/apple/mobiles/{base_model}/{model}-{storage}"

def format_price(price):
    """Formats the price with appropriate symbol and color emoji."""
    if price == "N/A":
        return "❌"
    try:
        price_val = float(price)
        return f"💰${price}:"  # Format price with 💰 emoji and $ symbol
    except:
        return "❌"  # Return ❌ for invalid prices

def fetch_prices_for_two_models(driver, models_pair, storages):
    """Fetch prices for two models and different storage options."""
    prices = []
    tabs = []

    for model in models_pair:
        for storage in storages:
            url = format_url(model, storage)
            logging.info(f"Opening URL: {url}")
            driver.execute_script(f"window.open('{url}', '_blank');")
            tabs.append((driver.window_handles[-1], model, storage, url))

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

        formatted_price = format_price(price)  # Format the price with the emoji and symbol
        prices.append((model, storage, formatted_price))
        driver.close()

    driver.switch_to.window(driver.window_handles[0])
    return prices

def group_models_by_series(models_data):
    """Groups models by their series (11, 12, 13, 14)."""
    series_groups = {}
    for model in models_data:
        series = model.split()[1][0:2]  # Gets "11", "12", "13", "14" from model name
        if series not in series_groups:
            series_groups[series] = []
        series_groups[series].append(model)
    return series_groups

@app.route('/')
def index():
    """Render the main page with the latest prices."""
    global prices, last_updated
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Only update if last update was more than an hour ago
    if not prices:
        logging.info("No prices available. Fetching prices now.")
        driver = setup_driver()
        models_pair = ["iphone-11", "iphone-12"]  # Example models to fetch
        storages = ["64gb", "128gb", "256gb"]
        prices = fetch_prices_for_two_models(driver, models_pair, storages)
        last_updated = time.time()
        driver.quit()

    return render_template('index.html', prices=prices, last_updated=last_updated, current_time=current_time)

@app.route('/refresh_prices')
def refresh_prices():
    """Handles refreshing the prices."""
    global prices, last_updated
    
    logging.info("Refresh prices button clicked.")
    
    # Only update if the last refresh was more than 1 hour ago
    if last_updated is None or (time.time() - last_updated) > 3600:
        driver = setup_driver()
        models_pair = ["iphone-11", "iphone-12"]  # Example models to fetch
        storages = ["64gb", "128gb", "256gb"]
        prices = fetch_prices_for_two_models(driver, models_pair, storages)
        last_updated = time.time()
        logging.info("Prices updated.")
        driver.quit()
        return redirect(url_for('index'))
    else:
        logging.info("Prices refresh attempted too soon.")
        return jsonify({"message": "Prices can only be refreshed once per hour."})

if __name__ == '__main__':
    # Fetch prices immediately when the script starts
    driver = setup_driver()
    models_pair = ["iphone-11", "iphone-12"]  # Example models to fetch
    storages = ["64gb", "128gb", "256gb"]
    prices = fetch_prices_for_two_models(driver, models_pair, storages)
    last_updated = time.time()
    logging.info("Prices fetched at the start of the application.")
    driver.quit()
    app.run(debug=True)
