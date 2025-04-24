import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

BASE_URL = "https://sgg.gouv.bj/documentheque/decrets/"
DOWNLOAD_PREFIX = "https://sgg.gouv.bj"

def download_decrets(output_dir="data/raw"):
    os.makedirs(output_dir, exist_ok=True)
    for page in range(1, 22):  
        url = f"{BASE_URL}{page}/"
        response = requests.get(url)
        soup = BeautifulSoup(response.content, "html.parser")
        links = soup.find_all("a", string="Télécharger")
        for link in links:
            href = link.get("href")
            if href and "decret-2024" in href:
                full_url = DOWNLOAD_PREFIX + href
                filename = href.split("/")[-2] + ".pdf"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(requests.get(full_url).content)



def download_pdf(url, output_dir="data/raw"):
    os.makedirs(output_dir, exist_ok=True)
    response = requests.get(url)
    
    if response.status_code == 200:
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        print("Téléchargement effecuté")
        return filepath  
    else:
        return f"Erreur : téléchargement échoué avec le code {response.status_code}"

