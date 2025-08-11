import os
import shutil
import glob
import nibabel as nib
import logging

import pandas as pd

from ..Processing.classification import compute_classification
from ..Utils.image_utils import is_image_eligible


def identify_sequences(input_folder: str, structure: str = "sectra_cdmedia", override: bool = False) -> None:
    """
    Runs the sequence classification model over each converted image inside the DICOM-conv for the input patient.
    The image name is appended with the sequence acronym, in addition to the csv file with the classification probabilities
    in case of uncertainties.
    OBS: some sequences are not included in the classification model, only the following are handled: [T1-w, T1-CE, T2, FLAIR]
    """
    if structure == "sectra_cdmedia":
        output_root = os.path.join(input_folder, 'DICOM-conv')
        if not os.path.exists(output_root):
            print(f"The DICOM folder with converted images does not exist at {output_root}")
            return
    else:
        output_root = input_folder

    nifti_files = glob.glob(os.path.join(output_root, "**/*.nii.gz"), recursive=True)
    for nf in nifti_files:
        try:
            compute_classification(nf, target_name="sequence", override=override)
        except Exception as e:
            print(f"Sequence classification on {nf} failed with {e}")
            continue

def sequence_selection(input_folder: str, override: bool = False) -> None:
    """

    """
    if not os.path.exists(input_folder):
        print(f"The folder with converted images does not exist at {input_folder}")
        return

    inv_dirs = []
    for _, dirs, _ in os.walk(input_folder):
        for d in dirs:
            inv_dirs.append(d)
        break

    for d in inv_dirs:
        try:
            sequence_selection_ts(input_folder=os.path.join(input_folder, d), override=override)
        except Exception as e:
            print(f"Sequence selection failed for timestamp {d} in {input_folder} with: {e}")


def sequence_selection_ts(input_folder: str, override: bool = False) -> None:
    """

    """
    exclusion_list = ["diffusion", "adc", "dwi", "localizer", "screensave", "tractography"]

    dest_filename = os.path.join(input_folder, "selection.csv")
    if os.path.exists(dest_filename) and not override:
        logging.info(f"Skipping sequence selection step, already performed in {input_folder}")
        return

    best_selected_files = {}
    best_selected_files["T1-w"] = None
    best_selected_files["T1-CE"] = None
    best_selected_files["T2"] = None
    best_selected_files["FLAIR"] = None
    nifti_files = glob.glob(os.path.join(input_folder, "**/*.nii.gz"), recursive=True)
    for nf in nifti_files:
        try:
            name_split = os.path.basename(nf).lower().split('-')
            if any(item in name_split for item in exclusion_list):
                logging.info(f"Discarded input MR scan {nf} because its name contains an exclusion tag")
                continue
            nf_nib = nib.load(nf)
            if not is_image_eligible(image=nf_nib):
                logging.info(f"Discarded input MR scan {nf} because the image is not eligible")
                continue
            seq = os.path.basename(nf).split('_')[-2]
            if best_selected_files[seq] is None:
                best_selected_files[seq] = {"file": nf, "spacings": nf_nib.header.get_zooms(), "dims": nf_nib.shape}
            else:
                curr_spac = nf_nib.header.get_zooms()
                curr_dim = nf_nib.shape
                best_spac = best_selected_files[seq]["spacings"]
                best_dim = best_selected_files[seq]["dims"]
                replace = False
                if min(curr_dim) > min(best_dim):
                    best_selected_files[seq] = {"file": nf, "spacings": nf_nib.header.get_zooms(), "dims": nf_nib.shape}
        except Exception as e:
            logging.error(f"Assessing MR scan selection status failed with {e}")
            continue

    # Saving the selection info
    try:
        pd.DataFrame([[key, value["file"]] for key, value in best_selected_files.items() if value is not None],
                     columns=["Sequence", "file"]).to_csv(dest_filename, index=False)
    except Exception as e:
        logging.error(f"Writing the selection info to csv failed with {e}")
