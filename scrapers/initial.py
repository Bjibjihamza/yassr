from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import re  # Pour extraire l'ID de l'URL

# Configuration de Selenium avec WebDriver Manager
options = Options()
options.add_argument("--headless")  # Exécuter en arrière-plan (optionnel)
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# URL de base sans numéro de page
BASE_URL = "https://www.moteur.ma/fr/voiture/achat-voiture-occasion/"

def extract_id_from_url(url):
    """Extrait l'ID de l'annonce depuis l'URL."""
    match = re.search(r"/detail-annonce/(\d+)/", url)
    return match.group(1) if match else "N/A"

def scrape_page(page_url):
    """Scrape les annonces d'une page donnée."""
    driver.get(page_url)
    
    # Attendre que les annonces chargent (timeout de 10 sec)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "row-item"))
        )
    except:
        print(f"Aucune annonce trouvée sur {page_url}")
        return []

    # Récupérer les annonces
    car_elements = driver.find_elements(By.CLASS_NAME, "row-item")
    data = []

    for car in car_elements:
        try:
            # Titre
            title_element = car.find_element(By.CLASS_NAME, "title_mark_model")
            title = title_element.text.strip() if title_element else "N/A"

            # Lien de l'annonce et extraction de l'ID
            try:
                link_element = car.find_element(By.XPATH, ".//h3[@class='title_mark_model']/a")
                link = link_element.get_attribute("href") if link_element else "N/A"
                ad_id = extract_id_from_url(link)  # Extraire l'ID
            except:
                link, ad_id = "N/A", "N/A"

            # Prix
            try:
                price_element = car.find_element(By.CLASS_NAME, "PriceListing")
                price = price_element.text.strip()
            except:
                price = "N/A"

            # Année, Ville, Carburant (On vérifie la présence)
            meta_elements = car.find_elements(By.TAG_NAME, "li")
            year = meta_elements[1].text.strip() if len(meta_elements) > 1 else "N/A"
            city = meta_elements[2].text.strip() if len(meta_elements) > 2 else "N/A"
            fuel = meta_elements[3].text.strip() if len(meta_elements) > 3 else "N/A"

            # Ajouter les données
            data.append({
                "ID": ad_id,
                "Titre": title,
                "Prix": price,
                "Année": year,
                "Ville": city,
                "Carburant": fuel,
                "Lien": link
            })

        except Exception as e:
            print(f"Erreur sur une annonce : {e}")

    return data

def scrape_multiple_pages(max_pages=4):
    """Scrape 4 pages du site en respectant le format de pagination (0, 30, 60, 90)"""
    all_data = []
    
    for page_offset in range(0, max_pages * 30, 30):  # Incrémente de 30 (0, 30, 60, 90)
        print(f"Scraping page avec offset {page_offset}...")
        page_url = f"{BASE_URL}{page_offset}" if page_offset > 0 else BASE_URL
        all_data.extend(scrape_page(page_url))
        time.sleep(3)  # Pause pour éviter le blocage

    return all_data

# Lancer le scraping
car_listings = scrape_multiple_pages(max_pages=4)  # Test sur 4 pages (0, 30, 60, 90)

# Sauvegarder les données dans un fichier CSV
df = pd.DataFrame(car_listings)
df.to_csv("moteur_ma_scraping.csv", index=False, encoding="utf-8-sig")

# Fermer le navigateur
driver.quit()

print("✅ Scraping terminé ! Données enregistrées dans moteur_ma_scraping.csv")
