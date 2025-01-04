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

# List of subscriber IDs (replace with your actual subscriber IDs)
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
    """Format the URL to scrape based on model and storage."""
    base_model = "-".join(model.split("-")[:2])
    return f"https://mobilemonster.com.au/sell-your-phone/apple/mobiles/{base_model}/{model}-{storage}"

def fetch_prices_for_two_models(driver, models_pair, storages):
    """Fetch prices for a pair of models with different storage options."""
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

        prices.append((model, storage, price))
        driver.close()

    driver.switch_to.window(driver.window_handles[0])
    return prices

def fetch_prices():
    """Fetch prices for all models and storages."""
    models = [
        "iphone-11", "iphone-11-pro", "iphone-11-pro-max",
        "iphone-12", "iphone-12-mini", "iphone-12-pro", "iphone-12-pro-max",
        "iphone-13", "iphone-13-mini", "iphone-13-pro", "iphone-13-pro-max",
        "iphone-14", "iphone-14-plus", "iphone-14-pro", "iphone-14-pro-max"
    ]
    storages = ["64gb", "128gb", "256gb", "512gb", "1tb"]

    results = {storage.upper(): [] for storage in storages}
    results["Model"] = []

    driver = setup_driver()
    
    try:
        for i in range(0, len(models), 2):
            models_pair = models[i:i + 2]
            logging.info(f"Processing models: {models_pair}")
            fetched_data = fetch_prices_for_two_models(driver, models_pair, storages)

            for model, storage, price in fetched_data:
                formatted_model = model.replace("-", " ").title()
                if formatted_model not in results["Model"]:
                    results["Model"].append(formatted_model)
                col_name = storage.upper()
                while len(results[col_name]) < len(results["Model"]) - 1:
                    results[col_name].append("")
                results[col_name].append(price)

        max_rows = max(len(results[col]) for col in results)
        for col in results:
            while len(results[col]) < max_rows:
                results[col].append("")

        return results
    finally:
        driver.quit()

@app.route('/')
def index():
    """Render the main page with the latest prices."""
    global prices, last_updated
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Only update if last update was more than an hour ago
    if not prices:
        logging.info("No prices available. Fetching prices now.")
        prices = fetch_prices()
        last_updated = time.time()

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
    # Fetch prices immediately when the script starts
    prices = fetch_prices()
    last_updated = time.time()
    logging.info("Prices fetched at the start of the application.")
    app.run(debug=True)
