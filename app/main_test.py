from app.services.ocr import process_file_for_signatures
from app.services.ocr import build_keywords_from_target
import os

#initiale (à ne normalement plus exécuter)
"""
from app.services.downloader import download_decrets
download_decrets()

"""

#cas 1
"""
from app.services.extractor import process_pdf_decret
from app.services.extractor import save_processed_data

data = process_pdf_decret("data/raw/decret-2024-003.pdf")
save_processed_data(data)

"""

"""
#cas 2
""" 


from app.services.ocr import process_file_for_signatures
from app.services.ocr import build_keywords_from_target
target_directory = "data/raw/decret-2024-003.pdf"

output_directory = "data/processed/signatures"

#process_file_for_signatures(target_directory, build_keywords_from_target(target_directory), output_directory)


"""
cas 3
"""

"""
from app.services.ocr import process_pdf_for_single_file

# Définition des constantes
MAX_TOTAL_CONTOURS_THRESHOLD = 8  # Nombre maximum de contours externes permis sur une page
MIN_MAP_AREA_RATIO = 0.45  # Ratio minimum de l'aire du plus grand contour / aire de la page
MAX_MAP_AREA_RATIO = 0.60  # Ratio maximum de l'aire du plus grand contour / aire de la page

# Définition des chemins de répertoires
target_directory = 'data/raw/decret-2024-1051.pdf'  
output_maps_directory = "data/processed/images"  # Dossier où les cartes extraites seront sauvegardées

# Appel à la fonction qui traite tous les PDF d'un dossier et extrait les cartes
final_results = process_pdf_for_single_file(
    target_directory,
    output_maps_directory,
    MAX_TOTAL_CONTOURS_THRESHOLD,
    MIN_MAP_AREA_RATIO,
    MAX_MAP_AREA_RATIO
)

##ces fichiers sont stockés dans image

"""


from app.services.downloader import download_pdf
download_pdf("https://sgg.gouv.bj/doc/decret-2024-003/download")

#cas du tableaux
from app.services.extractor import extract_tables_to_csv_with_caption

pdf_path = "data/raw/decret-2024-1065.pdf"
output_dir = "data/processed/tables"

extract_tables_to_csv_with_caption(pdf_path, output_dir)

