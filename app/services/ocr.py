import pytesseract
from pdf2image import convert_from_path
import re
import pytesseract
from pytesseract import Output
import fitz
from PIL import Image
import io
import os
import json
import cv2
import fitz  
import numpy as np

def extract_text_with_ocr(pdf_path):
    pages = convert_from_path(pdf_path)
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page, lang="fra")
    return text


def sanitize_filename(name):
    """Nettoie une chaîne pour l'utiliser comme nom de fichier sûr."""
    name = re.sub(r'[^\w\-_\. ]', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name

def ocr_page_find_and_crop_signatures(page, keyword_patterns, page_num, pdf_filename, output_dir):
    """
    Effectue l'OCR sur une page, trouve les mots-clés de signature,
    et sauvegarde une image rognée de la zone de signature probable.

    Args:
        page (fitz.Page): L'objet page PyMuPDF.
        keyword_patterns (dict): Dictionnaire {regex_pattern: full_name}.
        page_num (int): Le numéro de la page (commençant à 1).
        pdf_filename (str): Le nom du fichier PDF (pour nommer les sorties).
        output_dir (str): Le dossier où sauvegarder les images rognées.

    Returns:
        list: Une liste des noms complets pour lesquels une zone a été rognée et sauvegardée.
    """
    saved_crop_names = []
    img = None # Initialiser img
    try:
        # 1. Rendre la page en image PIL de haute qualité
        zoom = 6
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        img_width, img_height = img.size

        # 2. Effectuer l'OCR avec coordonnées
        ocr_data = pytesseract.image_to_data(img, lang='fra', output_type=Output.DICT, timeout=60) # Timeout augmenté
        n_boxes = len(ocr_data['level'])
        found_keywords_coords = {} 

        for i in range(n_boxes):
            if int(ocr_data['level'][i]) == 5: # Niveau mot
                confidence = int(ocr_data['conf'][i])
                text = ocr_data['text'][i].strip()

                # Seuil de confiance (ajustable)
                if confidence > 40 and text:
                    for keyword_regex, full_name in keyword_patterns.items():
                        # Utiliser re.fullmatch pour correspondre au mot entier
                        if re.fullmatch(keyword_regex, text, re.IGNORECASE):
                            if full_name not in found_keywords_coords:
                                found_keywords_coords[full_name] = []
                            # Stocker les coordonnées de ce mot-clé
                            found_keywords_coords[full_name].append({
                                'x': int(ocr_data['left'][i]),
                                'y': int(ocr_data['top'][i]),
                                'w': int(ocr_data['width'][i]),
                                'h': int(ocr_data['height'][i])
                            })
                            break

        for full_name, coords_list in found_keywords_coords.items():
            if not coords_list: continue

            ref_coord = coords_list[0]
            x, y, w, h = ref_coord['x'], ref_coord['y'], ref_coord['w'], ref_coord['h']

            pad_x = w * 2      # Marge horizontale
            pad_y_up = h * 8   # Marge vers le HAUT (CLÉ pour la signature manuscrite)
            pad_y_down = h * 3 # Marge vers le BAS (pour inclure le nom tapé)

            roi_x0 = max(0, x - pad_x)
            roi_y0 = max(0, y - pad_y_up)
            roi_x1 = min(img_width, x + w + pad_x)
            roi_y1 = min(img_height, y + h + pad_y_down)

            if roi_x1 > roi_x0 and roi_y1 > roi_y0:
                try:
                    cropped_image = img.crop((roi_x0, roi_y0, roi_x1, roi_y1))

                    base_pdf_name = sanitize_filename(os.path.splitext(pdf_filename)[0])
                    safe_signature_name = sanitize_filename(full_name)
                    output_filename = f"{base_pdf_name}_page{page_num}_{safe_signature_name}.png"
                    output_path = os.path.join(output_dir, output_filename)

                    cropped_image.save(output_path)
                    print(f"    -> Zone sauvegardée : {output_filename}")
                    if full_name not in saved_crop_names:
                         saved_crop_names.append(full_name)

                except RuntimeError as crop_err: 
                     print(f"    -> Erreur de rognage/sauvegarde pour {full_name} sur page {page_num}: {crop_err}")
                except Exception as save_e:
                     print(f"    -> Erreur de sauvegarde pour {full_name} sur page {page_num}: {save_e}")
            else:
                 print(f"    -> Boîte de rognage invalide calculée pour {full_name} sur page {page_num}.")


    except RuntimeError as timeout_error:
        print(f"  -> Timeout OCR sur {pdf_filename}, page {page_num}: {timeout_error}")
    except Exception as e:
        print(f"  -> Erreur OCR/Traitement sur {pdf_filename}, page {page_num}: {e}")
    finally:
        if img:
            del img

    return saved_crop_names

def process_pdf_for_signatures(pdf_path, keyword_patterns, output_dir):
    """
    Traite un fichier PDF entier, page par page, trouve et sauvegarde les zones de signature.

    Args:
        pdf_path (str): Chemin vers le fichier PDF.
        keyword_patterns (dict): Dictionnaire des mots-clés.
        output_dir (str): Dossier de sortie pour les images rognées.

    Returns:
        dict: Un dictionnaire {page_number: [list_of_saved_names]} pour ce PDF.
    """
    results_for_pdf = {}
    pdf_base_name = os.path.basename(pdf_path)
    print(f"Traitement de : {pdf_base_name}")
    doc = None
    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        print(f"  Nombre de pages : {num_pages}")

        for page_index in range(num_pages):
            page_num = page_index + 1
            print(f"  -- Analyse page {page_num}/{num_pages}...")
            page = doc.load_page(page_index)

            saved_names = ocr_page_find_and_crop_signatures(page, keyword_patterns, page_num, pdf_base_name, output_dir)

            if saved_names:
                results_for_pdf[page_num] = saved_names

            del page

    except Exception as e:
        print(f"Erreur lors de l'ouverture ou du traitement global de {pdf_path}: {e}")
    finally:
        if doc:
            doc.close()

    return results_for_pdf

def process_file_for_signatures(pdf_path, keyword_patterns, output_dir):
    """
    Traite un seul fichier PDF, trouve et sauvegarde les zones de signature.

    Args:
        pdf_path (str): Chemin complet vers le fichier PDF.
        keyword_patterns (dict): Dictionnaire des mots-clés pour identifier les signatures.
        output_dir (str): Dossier où sauvegarder toutes les images rognées.

    Returns:
        dict: Dictionnaire {page_number: [list_of_saved_names]}.
    """
    import os

    if not os.path.exists(pdf_path):
        print(f"ERREUR : Le fichier spécifié '{pdf_path}' n'existe pas.")
        return {}

    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Dossier de sortie créé : {output_dir}")
        except OSError as e:
            print(f"ERREUR : Impossible de créer le dossier de sortie '{output_dir}'. Erreur: {e}")
            return {}

    print(f"Traitement du fichier PDF : {pdf_path}")
    from app.services.ocr import process_pdf_for_signatures
    return process_pdf_for_signatures(pdf_path, keyword_patterns, output_dir)


def build_keywords_from_target(pdf_path):
    """
    Construit un dictionnaire SIGNATURE_KEYWORDS en se basant sur le PDF cible.

    Args:
        pdf_path (str): Chemin du fichier PDF.

    Returns:
        dict: Dictionnaire {regex: nom complet} à utiliser pour la détection de signatures.
    """
    base_filename = os.path.basename(pdf_path)

    json_filename = os.path.splitext(base_filename)[0] + ".json"

    json_path = os.path.join("data", "processed", json_filename)
    if not os.path.exists(json_path):
        print(f"⚠️ Fichier JSON introuvable pour {pdf_path} (attendu : {json_path})")
        return {}

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extraire les signataires
        signataires = data.get("signataires", [])
        keywords = {}

        for s in signataires:
            nom_complet = s.get("nom", "").strip()
            if nom_complet:
                nom_famille = nom_complet.split()[-1]
                regex = rf"\b{re.escape(nom_famille)}\b"
                keywords[regex] = nom_complet

        return keywords

    except Exception as e:
        print(f"❌ Erreur lors du chargement du fichier JSON : {e}")
        return {}
    
def find_and_extract_map_regions(page, page_num, pdf_filename, output_dir,
                                  max_total_contours=8,  # NOUVEAU Seuil: Max contours totaux sur la page
                                  min_map_area_ratio=0.45,  # NOUVEAU Seuil: Aire MIN pour la carte (ex: 45%)
                                  max_map_area_ratio=0.60  # NOUVEAU Seuil: Aire MAX pour la carte (ex: 60%)
                                 ):
    """
    Analyse l'image d'une page pour trouver des régions correspondant probablement
    à des cartes, en se basant sur le nombre total de contours et l'aire du plus grand.

    Args:
        page (fitz.Page): L'objet page PyMuPDF.
        page_num (int): Le numéro de la page.
        pdf_filename (str): Le nom du fichier PDF.
        output_dir (str): Le dossier où sauvegarder les images rognées.
        max_total_contours (int): Nombre maximum de contours externes permis sur la page.
        min_map_area_ratio (float): Ratio MINIMUM de l'aire du plus grand contour / aire page.
        max_map_area_ratio (float): Ratio MAXIMUM de l'aire du plus grand contour / aire page.

    Returns:
        list: Infos sur les régions sauvegardées (considérées comme cartes).
    """
    saved_maps_info = []
    img_cv = None

    try:
        # 1. Rendre la page en image
        zoom = 2
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        nparr = np.frombuffer(img_bytes, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_cv is None: return saved_maps_info
        page_height, page_width = img_cv.shape[:2]
        page_area = page_width * page_height

        # 2. Prétraitement et recherche de contours EXTERNES
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        total_contours_found = len(contours)

        print(f"  -- Page {page_num}: {total_contours_found} contours externes trouvés.")

        # *** NOUVEAU Filtre 1: Nombre Total de Contours ***
        if total_contours_found > 0 and total_contours_found <= max_total_contours:
            print(f"     -> Nombre total de contours ({total_contours_found}) <= {max_total_contours}. Vérification du plus grand...")

            # Trouver le plus grand contour
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            area_ratio = area / page_area

            print(f"        -> Plus grand contour trouvé (Aire: {area_ratio * 100:.1f}% de la page). Vérification fourchette [{min_map_area_ratio*100:.1f}% - {max_map_area_ratio*100:.1f}%]...")

            # *** NOUVEAU Filtre 2: Fourchette d'Aire du Plus Grand Contour ***
            if area_ratio >= min_map_area_ratio and area_ratio <= max_map_area_ratio:
                print(f"           -> Aire dans la fourchette cible ! Extraction...")
                map_index = 1  # On suppose une seule carte par page avec cette méthode
                x, y, w, h = cv2.boundingRect(largest_contour)

                # Rogner et Sauvegarder (avec padding)
                padding = 5
                crop_x = max(0, x - padding)
                crop_y = max(0, y - padding)
                crop_w = min(page_width - crop_x, w + 2 * padding)
                crop_h = min(page_height - crop_y, h + 2 * padding)

                if crop_w > 0 and crop_h > 0:
                    final_cropped_region = img_cv[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
                    try:
                        base_pdf_name = sanitize_filename(os.path.splitext(pdf_filename)[0])
                        # Nom de fichier simplifié car on s'attend à une seule carte
                        output_filename = f"{base_pdf_name}_page{page_num}_map.png"
                        output_path = os.path.join(output_dir, output_filename)
                        cv2.imwrite(output_path, final_cropped_region)
                        saved_maps_info.append({
                            "filename": output_filename, "page": page_num, "map_index": map_index,
                            "x": crop_x, "y": crop_y, "width": crop_w, "height": crop_h,
                            "area_ratio": area_ratio
                        })
                    except Exception as save_e:
                        print(f"           -> ERREUR sauvegarde région {output_filename}: {save_e}")
                else:
                    print(f"           -> Boîte de rognage invalide.")
            else:
                print(f"           -> Rejeté : Aire ({area_ratio * 100:.1f}%) hors fourchette.")

    except Exception as e:
        print(f"  -> ERREUR lors du traitement d'image de la page {page_num}: {e}")
        import traceback
        traceback.print_exc()
    finally:
         if img_cv is not None: del img_cv

    return saved_maps_info


def process_pdf_for_maps(pdf_path, output_dir, max_total_contours, min_map_area_ratio, max_map_area_ratio):
    """ Traite un PDF pour trouver les cartes basées sur les nouveaux critères. """
    results_for_pdf = {}
    pdf_base_name = os.path.basename(pdf_path)
    print(f"Traitement (Cartes) de : {pdf_base_name}")
    doc = None
    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        print(f"  Nombre de pages : {num_pages}")

        for page_index in range(num_pages):
            page_num = page_index + 1
            page = doc.load_page(page_index)
            saved_regions = find_and_extract_map_regions(page, page_num, pdf_base_name, output_dir,
                                                         max_total_contours, min_map_area_ratio, max_map_area_ratio)
            if saved_regions:
                results_for_pdf[page_num] = saved_regions
            del page

    except Exception as e:
        print(f"ERREUR lors de l'ouverture/traitement global (Cartes) de {pdf_path}: {e}")
    finally:
        if doc: doc.close()
    return results_for_pdf


def process_pdf_for_single_file(pdf_path, output_dir, max_total_contours, min_map_area_ratio, max_map_area_ratio):
    """ Traite un seul fichier PDF pour extraire les cartes. """
    results_for_pdf = {}
    pdf_base_name = os.path.basename(pdf_path)
    print(f"Traitement (Cartes) de : {pdf_base_name}")

    try:
        pdf_results = process_pdf_for_maps(pdf_path, output_dir, max_total_contours, min_map_area_ratio, max_map_area_ratio)
        if pdf_results:
            results_for_pdf[pdf_base_name] = pdf_results
    except Exception as e:
        print(f"ERREUR lors du traitement du fichier PDF {pdf_path}: {e}")
    
    return results_for_pdf

