import os
import json
import re
from openai import AzureOpenAI
from dotenv import load_dotenv
import pytesseract

load_dotenv()

api_key = os.getenv("AZURE_OPENAI_API_KEY")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
model = os.getenv("AZURE_OPENAI_MODEL")

client = AzureOpenAI(
    api_key=api_key,
    api_version=api_version,
    azure_endpoint=endpoint
)

def extract_metadata_with_gpt(text):
    prompt = (
        "Voici un décret officiel extrait via OCR.\n"
        "Analyse ce texte et fournis les métadonnées en format JSON structuré comme suit :\n\n"
        "- numéro_decret\n"
        "- date_de_publication\n"
        "- ministere_emetteur\n"
        "- objet\n"
        "- preambule (ou introduction)\n"
        "- contenu_des_articles (clé = Article_X, valeur = contenu)\n"
        "- definitions (si présentes, termes juridiques spécifiques)\n"
        "- signataires : liste avec 'nom' et 'fonction'\n"
        "- tableaux : résumé ou description\n"
        "- graphiques_schemas : résumé ou description\n"
        "- logos_cachets  : résumé ou description\n\n"
        "Renvoie uniquement un objet JSON sans explication autour. Voici le texte à analyser :\n\n"
        f"{text}"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )

    raw_response = response.choices[0].message.content
    json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)

    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return "Erreur : JSON mal formé dans la réponse."
    else:
        return "Erreur : Aucun JSON trouvé dans la réponse."
