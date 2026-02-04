import os
import shutil
import glob
import nibabel as nib
import logging
import numpy as np

import pandas as pd

from ..Processing.segmentation import compute_segmentation
from ..Utils.image_utils import is_image_eligible


def identify_structure_extent(input_filename: str, structure_name: str) -> int:
    try:
        model_name = None
        if structure_name == "Lungs":
            model_name = "CT_Lungs"
        if not model_name:
            raise ValueError(f"No model could be found for {structure_name}.")

        compute_segmentation(input_filename=input_filename, model_name=model_name, override=False)
        structure_mask_fn = os.path.join(os.path.dirname(input_filename), os.path.basename(input_filename).split('.')[0] + '_annotation-' + structure_name + '.nii.gz')
        if not os.path.exists(structure_mask_fn):
            raise ValueError(f"Structure mask could not be found on disk with value {structure_mask_fn}.")
        structure_nib = nib.load(structure_mask_fn)
        structure_array = structure_nib.get_fdata()[:].astype('uint8')
        pixels_per_slice = structure_array.sum(axis=(0, 1))
        # @TODO. The threshold should be based of the type of structure and also the pixel spacing?
        valid_slices = (pixels_per_slice * np.prod(structure_nib.header.get_zooms()[0:2])) >= 2000
        count_valid = valid_slices.sum()
        return count_valid

    except Exception as e:
        print(f"Structure segmentation in {input_filename} failed with {e}")

def ct_sequence_selection(input_folder: str, override: bool = False) -> None:
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
            ct_sequence_selection_ts(input_folder=os.path.join(input_folder, d), override=override)
        except Exception as e:
            print(f"Sequence selection failed for timestamp {d} in {input_folder} with: {e}")


def ct_sequence_selection_ts(input_folder: str, override: bool = False) -> None:
    """
    #@TODO. Should ensure all CTs are in the same folder, for the given timestamp!
    """
    exclusion_list = ["diffusion", "adc", "dwi", "localizer", "screensave", "tractography"]

    dest_filename = os.path.join(input_folder, "selection.csv")
    if os.path.exists(dest_filename) and not override:
        logging.info(f"Skipping sequence selection step, already performed in {input_folder}")
        return

    best_selected_files = {}
    best_selected_files["HR"] = None
    nifti_files = [x for x in glob.glob(os.path.join(input_folder, "**/*.nii.gz"), recursive=True) if ("annotation" or "label") not in x]
    for nf in nifti_files:
        try:
            name_split = os.path.basename(nf).lower().split('-')
            if any(item in name_split for item in exclusion_list):
                logging.info(f"Discarded input CT scan {nf} because its name contains an exclusion tag")
                continue
            nf_nib = nib.load(nf)
            if not is_image_eligible(image=nf_nib):
                logging.info(f"Discarded input CT scan {nf} because the image is not eligible")
                continue
            seq = "HR"
            structure_extent = identify_structure_extent(input_filename=os.path.join(input_folder, nf),
                                                         structure_name="Lungs")
            if best_selected_files[seq] is None:
                best_selected_files[seq] = {"file": nf, "spacings": nf_nib.header.get_zooms(), "dims": nf_nib.shape, "structure_extent": structure_extent}
            else:
                curr_spac = nf_nib.header.get_zooms()
                curr_dim = nf_nib.shape
                best_spac = best_selected_files[seq]["spacings"]
                best_dim = best_selected_files[seq]["dims"]
                best_extent = best_selected_files[seq]["structure_extent"]
                replace = False
                relative_extent = structure_extent * best_spac[2]
                if relative_extent > (best_extent * best_spac[2]): # and min(curr_dim) < min(best_dim):
                    replace = True

                if replace:
                    best_selected_files[seq] = {"file": nf, "spacings": nf_nib.header.get_zooms(), "dims": nf_nib.shape,
                                                "structure_extent": structure_extent}
        except Exception as e:
            logging.error(f"Assessing CT scan selection status failed with {e}")
            continue

    # Saving the selection info
    try:
        pd.DataFrame([[key, value["file"]] for key, value in best_selected_files.items() if value is not None],
                     columns=["Sequence", "file"]).to_csv(dest_filename, index=False)
    except Exception as e:
        logging.error(f"Writing the selection info to csv failed with {e}")
