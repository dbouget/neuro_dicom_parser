import os
import shutil
import requests
import zipfile
import logging


def ensure_models_present():
    models_path = os.path.join(os.path.dirname(__file__), "..", "Models")
    urls = {"MRI_SequenceClassifier": "https://github.com/raidionics/Raidionics-models/releases/download/v1.3.0-rc/Raidionics-MRI_SequenceClassifier-v13.zip",
            "CT_Lungs": "https://github.com/raidionics/Raidionics-models/releases/download/v1.3.0-rc/Raidionics-CT_Lungs-v13.zip"}
    for model_key in urls.keys():
        download_path = os.path.join(models_path, "..", model_key+"_model.zip")

        if os.path.exists(os.path.join(models_path, model_key)):
            return  # Already extracted
        logging.info("Downloading model...")
        os.makedirs(models_path, exist_ok=True)
        headers = {}
        response = requests.get(urls[model_key], headers=headers, stream=True)
        response.raise_for_status()

        if response.status_code == requests.codes.ok:
            with open(download_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=1048576):
                    f.write(chunk)
        with zipfile.ZipFile(download_path, 'r') as zip_ref:
            zip_ref.extractall(models_path)
        logging.info(f"Extracted model in {models_path}")
        os.remove(download_path)