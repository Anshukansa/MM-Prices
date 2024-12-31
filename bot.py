import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException,
)
import time

def setup_driver(headless=True):
    """
    Sets up the Selenium WebDriver with desired options for Heroku.
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless")  # Run in headless mode
    
    # Add necessary arguments for Heroku
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--proxy-server='direct://'")
    chrome_options.add_argument("--proxy-bypass-list=*")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-browser-side-navigation")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")  # Disable images for faster loading

    # Set the binary location for Chrome
    chrome_binary_path = os.environ.get("GOOGLE_CHROME_BIN", "/app/.apt/usr/bin/google-chrome")
    chrome_options.binary_location = chrome_binary_path

    # Set the Chromedriver path
    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH", "/app/.chromedriver/bin/chromedriver")

    # Initialize WebDriver using the specified paths
    service = ChromeService(executable_path=chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
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

def main():
    # Initialize the WebDriver
    # Set headless=False for debugging to see the browser actions
    driver = setup_driver(headless=True)

    try:
        # ABC Bullion URL
        abc_bullion_url = "https://www.abcbullion.com.au/store/gold/gabgtael375g-abc-bullion-tael-cast-bar"
        abc_price = get_abc_bullion_price(driver, abc_bullion_url)

        # Aarav Bullion URL
        aarav_bullion_url = "https://aaravbullion.in/"
        aarav_price = get_aarav_bullion_prices(driver, aarav_bullion_url)

        # If you wish to handle more entries in the future, consider storing them appropriately

    finally:
        # Close the browser once done
        driver.quit()
        # print("Browser closed.")

if __name__ == "__main__":
    main()
