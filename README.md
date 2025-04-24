# 📄 Décrets PDF Analyzer - API FastAPI

Une API REST légère pour :
- Télécharger et analyser des décrets au format PDF
- Extraire automatiquement les **signatures** présentes dans le document
- Détecter et extraire les **cartes géographiques**
- Servir les images extraites via des URLs
- Générer des pages HTML d’aperçu
-Générer et visualiser les tableaux du document

## 🚀 Fonctionnalités

- ✅ Téléchargement d’un PDF depuis une URL
- ✍️ Détection et extraction OCR des signatures
- 🗺️ Détection des cartes et tableaux via analyse d’image
- 🌐 Exposition des images via des routes API
- 🖼️ Visualisation HTML des signatures et cartes

# Installation & Lancement
# Installer les dépendances
pip install -r requirements.txt

# Lancer le serveur FastAPI
uvicorn app.main:app --reload


Une fois lancée, rendez-vous dans votre navigateur à :http://localhost:8000/docs

Tester les routes en insérant les input attendus dans les champs de la documentation.

Toutes les routes de type /image-all/ permettent un aperçu visuel direct des résultats.
Vous pouvez copier l’URL retournée et la coller dans votre navigateur pour visualiser le contenu.
Exemple d'url retournée http://127.0.0.1:8000/api/maps/image-all/decret-2024-1051.pdf 

🔍 Notes importantes

    Toutes les routes de type /...-all/ permettent un aperçu visuel direct des résultats.

        Par exemple :
        http://127.0.0.1:8000/api/maps/image-all/decret-2024-1051.pdf

    ⚠️ Avant de tester la route d’affichage des toutes signatures,images, il faut préalablement extraire les signatures ou images du document PDF.

