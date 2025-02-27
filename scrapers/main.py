import os
import time
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from tqdm import tqdm

# Selenium Configuration
options = Options()
options.add_argument("--headless")  # Run without opening a browser
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Load car listing URLs from CSV file
df = pd.read_csv("moteur_ma_scraping.csv")

# Image Storage Directory
IMAGE_DIR = "car_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

def download_image(img_url, folder_path, img_name):
    """Download an image using Selenium to bypass restrictions."""
    try:
        driver.get(img_url)  # Open image in browser
        time.sleep(2)  # Give time to load

        # Get the image source from the opened page
        img_element = driver.find_element(By.TAG_NAME, "img")
        img_src = img_element.get_attribute("src")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.moteur.ma/"
        }

        response = requests.get(img_src, headers=headers, stream=True, timeout=10)
        if response.status_code == 200:
            img_path = os.path.join(folder_path, img_name)
            with open(img_path, "wb") as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            return img_path
        else:
            print(f"❌ Failed to download {img_src} (Status: {response.status_code})")
    except Exception as e:
        print(f"❌ Error downloading {img_url}: {e}")
    return None

def scrape_car_details(url, car_id):
    """Scrape detailed car data, including images"""
    driver.get(url)
    
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "car-detail"))
        )
    except:
        print(f"⚠️ No data found for {url}")
        return None

    time.sleep(3)  # Allow JavaScript to load

    # Create a folder to store images for this car
    car_folder = os.path.join(IMAGE_DIR, str(car_id))
    os.makedirs(car_folder, exist_ok=True)

    # Fetch all car images
    image_elements = driver.find_elements(By.XPATH, "//img[@data-u='image']")
    image_paths = []

    if len(image_elements) == 0:
        print(f"⚠️ No images found for {url}")
    else:
        print(f"🔎 Found {len(image_elements)} images for car {car_id}")

    for index, img_elem in enumerate(image_elements):
        img_url = img_elem.get_attribute("src")
        print(f"🔗 Image URL: {img_url}")

        if img_url and "https" in img_url:
            img_name = f"{index+1}.jpg"
            img_path = download_image(img_url, car_folder, img_name)
            if img_path:
                image_paths.append(img_path)

    # Fetch car details (Mileage, Transmission, Fuel, etc.)
    details = {}
    details_section = driver.find_elements(By.CLASS_NAME, "detail_line")

    for detail in details_section:
        try:
            key_element = detail.find_element(By.CLASS_NAME, "col-md-6")
            value_element = detail.find_element(By.CLASS_NAME, "text_bold")
            key = key_element.text.strip()
            value = value_element.text.strip()
            details[key] = value
        except:
            continue

    # Fetch car description
    try:
        description = driver.find_element(By.CLASS_NAME, "options").text.strip()
    except:
        description = "N/A"

    # **🚀 Fix: Save images in a comma-separated format instead of a list**
    image_column_value = "; ".join(image_paths) if image_paths else "No Images Found"

    return {
        "ID": car_id,
        "URL": url,
        "Mileage": details.get("Kilométrage", "N/A"),
        "Year": details.get("Année", "N/A"),
        "Transmission": details.get("Boite de vitesses", "N/A"),
        "Fuel": details.get("Carburant", "N/A"),
        "Date": details.get("Date", "N/A"),
        "Fiscal Power": details.get("Puissance fiscale", "N/A"),
        "Doors": details.get("Nombre de portes", "N/A"),
        "First Owner": details.get("Première main", "N/A"),
        "Cleared Vehicle": details.get("Véhicule dédouané", "N/A"),
        "Description": description,
        "Images": image_column_value  # ✅ **Fix: Save as a string**
    }

# List to store scraped car details
car_details_list = []

# Scrape details for each car and show progress using tqdm
for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Scraping cars"):
    car_id = row["Lien"].split("/")[-2]  # Extract ID from URL
    car_details = scrape_car_details(row["Lien"], car_id)
    if car_details:
        car_details_list.append(car_details)

# Save details in a new CSV file with English column names
df_details = pd.DataFrame(car_details_list)
df_details.to_csv("moteur_ma_details_en.csv", index=False, encoding="utf-8-sig")

# Close browser
driver.quit()

print("✅ Scraping completed! Data saved in moteur_ma_details_en.csv")
