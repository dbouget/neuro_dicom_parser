import os
import shutil
import requests
import zipfile
import logging


def ensure_models_present():
    models_path = os.path.join(os.path.dirname(__file__), "..", "Models")
    url = "https://github.com/raidionics/Raidionics-models/releases/download/v1.3.0-rc/Raidionics-MRI_SequenceClassifier-v13.zip"
    download_path = os.path.join(models_path, "..", "seq_model.zip")

    if os.path.exists(os.path.join(models_path, "MRI_SequenceClassifier")):
        return  # Already extracted
    logging.info("Downloading models...")
    os.makedirs(models_path, exist_ok=True)
    headers = {}
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    if response.status_code == requests.codes.ok:
        with open(download_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1048576):
                f.write(chunk)
    with zipfile.ZipFile(download_path, 'r') as zip_ref:
        zip_ref.extractall(models_path)
    logging.info(f"Extracted models in {models_path}")
    os.remove(download_path)