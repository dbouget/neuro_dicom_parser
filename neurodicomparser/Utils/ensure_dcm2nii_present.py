import os
import platform
import shutil
import requests
import zipfile
import logging
import stat


def ensure_dcm2nii_present():
    url = None
    if platform.system() == "Darwin":
        url = "https://github.com/raidionics/Raidionics-dependencies/releases/download/v1.0.0/MRIcroGL-macOS.zip"
    elif platform.system() == "Linux":
        url = "https://github.com/raidionics/Raidionics-dependencies/releases/download/v1.0.0/MRIcroGL-linux.zip"
    elif os.name == "nt":
        pass

    dest_path = os.path.join(os.path.dirname(__file__), "..")
    download_path = os.path.join(dest_path, "..", "ANTsX.tar.gz")

    if os.path.exists(os.path.join(dest_path, "MRIcroGL")):
        logging.info("MRIcroGL found - skipping.")
        return
    logging.info("Downloading MRIcroGL...")
    headers = {}
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()

    if response.status_code == requests.codes.ok:
        with open(download_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1048576):
                f.write(chunk)

    with zipfile.ZipFile(download_path, 'r') as zip_ref:
        zip_ref.extractall(dest_path)
    logging.info(f"Extracted MRIcroGL in {dest_path}")

    if os.name != 'nt':  # Skip on Windows
        executable_path = os.path.join(dest_path, "MRIcroGL", "Resources", "dcm2niix")
        st = os.stat(executable_path)
        os.chmod(executable_path, st.st_mode | stat.S_IEXEC)

    os.remove(download_path)
