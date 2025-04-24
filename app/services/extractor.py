import os
import json
from app.services.ocr import extract_text_with_ocr
from app.services.openai_helper import extract_metadata_with_gpt
import fitz  
import pytesseract
from PIL import Image
import cv2
import numpy as np
from pdf2image import convert_from_path
from pathlib import Path
import pandas as pd
import re
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TesseractCliOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


def process_pdf_decret(pdf_path):
    text = extract_text_with_ocr(pdf_path)
    return extract_metadata_with_gpt(text)
def save_processed_data(data):
    if "numéro_decret" in data:
        numero_decret = data["numéro_decret"]
    else:
        numero_decret = "inconnu"
        print("Avertissement : La clé 'numero_decret' est manquante ou invalide.")

    filename = f"decret-{numero_decret}.json"
    
    processed_dir = "data/processed/"
    if not os.path.exists(processed_dir):
        os.makedirs(processed_dir)
    
    file_path = os.path.join(processed_dir, filename)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"Les données traitées ont été enregistrées dans {file_path}")


def sanitize_filename(text):
    """Supprime ou remplace les caractères interdits dans les noms de fichiers."""
    return re.sub(r'[\\/*?:"<>|]', "_", text)

def extract_tables_to_csv_with_caption(input_doc_path, csv_output_folder):
    """
    Extrait tous les tableaux d'un document PDF, y compris leurs légendes, 
    et les sauvegarde en fichiers CSV. Retourne la liste des captions des tableaux extraits.
    """
    input_doc_path = Path(input_doc_path)
    csv_output_folder = Path(csv_output_folder)
    csv_output_folder.mkdir(parents=True, exist_ok=True)

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    pipeline_options.ocr_options = TesseractCliOcrOptions(force_full_page_ocr=True)

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    result = converter.convert(input_doc_path)
    doc = result.document
    tables = doc.tables

    if not tables:
        print("❌ Aucun tableau trouvé.")
        return []

    document_name = input_doc_path.stem.replace("-", "_")
    captions = []

    for idx, table in enumerate(tables, 1):
        try:
            caption = table.caption_text(doc)
            if not caption:
                caption = f"{document_name}_tableau_{idx}"

            print(f"🔍 Traitement du tableau {idx} : {caption}")
            captions.append(caption)

            df = table.export_to_dataframe()

            caption_df = pd.DataFrame([[caption] + [""] * (len(df.columns) - 1)], columns=df.columns)
            df_with_caption = pd.concat([caption_df, df], ignore_index=True)

            filename = sanitize_filename(caption)
            output_path = csv_output_folder / f"{filename}.csv"
            df_with_caption.to_csv(output_path, index=False)
            print(f"✅ Tableau {idx} sauvegardé dans : {output_path}")
        except Exception as e:
            print(f"⚠️ Erreur lors de l'export du tableau {idx} : {e}")

    return captions