from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from app.services.downloader import download_pdf
from app.services.extractor import process_pdf_decret, save_processed_data
from app.services.ocr import build_keywords_from_target, process_file_for_signatures
from app.services.ocr import process_pdf_for_single_file  
from app.services.extractor import extract_tables_to_csv_with_caption
import os
import requests
import re
from pathlib import Path
import pandas as pd
router = APIRouter(prefix="/api")

SIGNATURES_DIR = "data/processed/signatures"
RAW_DIR = "data/raw"

@router.get("/analyze-from-url")
def analyze_pdf_from_url(url: str = Query(..., description="URL du PDF à analyser")):
    """
    Télécharge et extraire les métadonnées à partir d'url
    Exemple d'url: https://sgg.gouv.bj/doc/decret-2024-1051/download 
    """
    url = url.strip().strip('"')
    downloaded_path = download_pdf(url)

    if isinstance(downloaded_path, str) and downloaded_path.startswith("Erreur"):
        return {"status": "failed", "message": downloaded_path}

    data = process_pdf_decret(downloaded_path)
    save_processed_data(data)
    return {"status": "success", "data": data}


@router.get("/signatures/{decret_filename}")
def extract_signatures(decret_filename: str):
    """
    Extrait les signatures d'un décret donné en pdf. 
    Exemple : decret-2024-1051.pdf
    """
    pdf_path = os.path.join(RAW_DIR, decret_filename)

    # Si le fichier n'existe pas localement
    if not os.path.exists(pdf_path):
        decret_name = decret_filename.replace(".pdf", "")
        url = f"https://sgg.gouv.bj/doc/{decret_name}/download"

        try:
            response = requests.get(url)
            if response.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Impossible de télécharger le fichier depuis {url}")

            with open(pdf_path, "wb") as f:
                f.write(response.content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erreur lors du téléchargement : {e}")

    try:
        # 1. Construire les mots-clés
        keywords = build_keywords_from_target(pdf_path)

        # 2. Lancer le traitement OCR
        result = process_file_for_signatures(pdf_path, keywords, SIGNATURES_DIR)

        # 3. Récupérer tous les fichiers image générés pour ce décret
        base_name = os.path.splitext(decret_filename)[0]
        signature_images = [
            f for f in os.listdir(SIGNATURES_DIR)
            if f.startswith(base_name) and f.endswith(".png")
        ]

        # 4. Retourner une liste de liens directement utilisables dans un <img>
        image_urls = [f"/api/signatures/image/{filename}" for filename in signature_images]
        return {"images": image_urls}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement OCR : {e}")

@router.get("/signatures/image/{filename}")
def get_signature_image(filename: str):
    """
    Sert une image de signature.
    Exemple : decret-2024-1051_page2_Romuald_WADAGNI.png
    """
    image_path = os.path.join(SIGNATURES_DIR, filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image non trouvée.")
    
    return FileResponse(image_path, media_type="image/png")


@router.get("/signatures/image-all/{decret_filename}", response_class=HTMLResponse)
def show_all_signature_images(decret_filename: str):
    """
    Génère une page HTML affichant toutes les signatures extraites pour un décret donné.
    Exemple : decret-2024-1051.pdf
    """
    base_name = os.path.splitext(decret_filename)[0]
    matching_images = [
        f for f in os.listdir(SIGNATURES_DIR)
        if f.startswith(base_name) and f.endswith(".png")
    ]

    if not matching_images:
        raise HTTPException(status_code=404, detail="Aucune image de signature trouvée.")

    html_content = f"""
    <html>
    <head>
        <title>Signatures extraites - {decret_filename}</title>
        <style>
            body {{ font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px; }}
            .image-block {{ 
                background: #fff; 
                padding: 15px; 
                margin-bottom: 20px; 
                border-radius: 8px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                max-width: 650px;
            }}
            .image-block img {{ max-width: 100%; border: 1px solid #ccc; }}
        </style>
    </head>
    <body>
        <h2>Signatures extraites de : {decret_filename}</h2>
    """

    for filename in matching_images:
        img_url = f"/api/signatures/image/{filename}"
        html_content += f"""
        <div class="image-block">
            <p>{filename}</p>
            <img src="{img_url}" alt="{filename}">
        </div>
        """

    html_content += "</body></html>"
    return HTMLResponse(content=html_content)



MAPS_DIR = "data/processed/images"

#  Paramètres pour la détection de cartes
MAX_TOTAL_CONTOURS_THRESHOLD = 8
MIN_MAP_AREA_RATIO = 0.45
MAX_MAP_AREA_RATIO = 0.60

@router.get("/maps/{decret_filename}")
def extract_maps(decret_filename: str):
    """
    Extrait les cartes d'un PDF donné, et retourne les liens vers les images extraites.
    Exemple : decret-2024-1051.pdf
    """
    pdf_path = os.path.join("data/raw", decret_filename)
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Fichier PDF non trouvé.")

    try:
        result = process_pdf_for_single_file(
            pdf_path,
            MAPS_DIR,
            MAX_TOTAL_CONTOURS_THRESHOLD,
            MIN_MAP_AREA_RATIO,
            MAX_MAP_AREA_RATIO
        )

        base_name = os.path.splitext(decret_filename)[0]
        map_images = [
            f for f in os.listdir(MAPS_DIR)
            if f.startswith(base_name) and f.endswith(".png")
        ]

        image_urls = [f"/api/maps/image/{img}" for img in map_images]
        return {"maps": image_urls}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du traitement du PDF : {e}")


@router.get("/maps/image/{filename}")
def get_map_image(filename: str):
    """
    Sert une image de carte extraite.
    Exemple : decret-2024-1051_page48_map.png
    """
    image_path = os.path.join(MAPS_DIR, filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image non trouvée.")
    
    return FileResponse(image_path, media_type="image/png")


@router.get("/maps/image-all/{decret_filename}", response_class=HTMLResponse)
def show_all_maps_html(decret_filename: str):
    """
    Affiche une page HTML avec toutes les cartes extraites d'un PDF.
    Exemple : decret-2024-1051.pdf
    """
    base_name = os.path.splitext(decret_filename)[0]
    map_images = [
        f for f in os.listdir(MAPS_DIR)
        if f.startswith(base_name) and f.endswith(".png")
    ]

    if not map_images:
        raise HTTPException(status_code=404, detail="Aucune carte extraite trouvée.")

    html_content = f"""
    <html>
    <head><title>Cartes extraites - {decret_filename}</title></head>
    <body>
        <h2>Cartes extraites de : {decret_filename}</h2>
    """
    for img in map_images:
        html_content += f"""
        <div style="margin-bottom: 20px;">
            <p>{img}</p>
            <img src="/api/maps/image/{img}" style="max-width:600px;">
        </div>
        """
    html_content += "</body></html>"

    return html_content

@router.get("/extract-tables")
def extract_and_show_tables(
    filename: str = Query(..., description="Nom du fichier PDF à traiter, ex: decret-2024-1065.pdf")
):
    """
    Extrait les tableaux d'un fichier PDF présent dans 'data/raw', les sauvegarde en CSV,
    puis retourne leur contenu.
    """
    output_folder: str = "data/processed/tables"
    try:
        pdf_path = Path("data/raw") / filename
        if not pdf_path.exists():
            return {"status": "error", "message": f"Fichier introuvable : {pdf_path}"}

        captions = extract_tables_to_csv_with_caption(pdf_path, output_folder)
        if not captions:
            return {"status": "no_tables_found", "message": "Aucun tableau trouvé dans ce document."}

        tables_data = []
        for caption in captions:
            sanitized_name = "".join(c if c.isalnum() or c in ('_', '-') else "_" for c in caption)
            csv_path = Path(output_folder) / f"{sanitized_name}.csv"
            if csv_path.exists():
                df = pd.read_csv(csv_path)
                tables_data.append({
                    "caption": caption,
                    "data": df.fillna("").to_dict(orient="records")
                })

        return {
            "status": "success",
            "tables_extracted": len(tables_data),
            "tables": tables_data
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    