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


def identify_relevant_dicom_metadata(input_filename: str) -> dict:
    try:

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
    @TODO2. Should open the selection.csv maybe at the start if it exists, to trigger a recompute if empty?
    @TODO3. Should also open the DICOM metadata, there might be relevant tag: 0018|0010
    """
    exclusion_list = ["diffusion", "adc", "dwi", "localizer", "screensave", "tractography", "derived", "secondary"]

    dest_filename = os.path.join(input_folder, "selection.csv")
    if os.path.exists(dest_filename) and not override:
        logging.info(f"Skipping sequence selection step, already performed in {input_folder}")
        return

    best_selected_files = {}
    best_selected_files["HR"] = None
    all_files_info = {}
    nifti_files = [x for x in glob.glob(os.path.join(input_folder, "**/*.nii.gz"), recursive=True) if ("annotation" or "label") not in x]
    for nf in nifti_files:
        try:
            name_split = os.path.basename(nf).lower().split('_')
            nf_nib = nib.load(nf)
            if not is_image_eligible(image=nf_nib):
                logging.info(f"Discarded input CT scan {nf} because the image is not eligible")
                continue
            seq = "HR"
            structure_extent = identify_structure_extent(input_filename=os.path.join(input_folder, nf),
                                                         structure_name="Lungs")
            all_files_info[nf] = {"file": nf, "spacings": nf_nib.header.get_zooms(), "dims": nf_nib.shape,
                                  "structure_extent": structure_extent}
            if any(item in name_split for item in exclusion_list):
                logging.info(f"Discarded input CT scan {nf} because its name contains an exclusion tag")
                continue

            if best_selected_files[seq] is None:
                best_selected_files[seq] = {"file": nf, "spacings": nf_nib.header.get_zooms(), "dims": nf_nib.shape, "structure_extent": structure_extent}
            else:
                curr_spac = nf_nib.header.get_zooms()
                curr_dim = nf_nib.shape
                best_spac = best_selected_files[seq]["spacings"]
                best_dim = best_selected_files[seq]["dims"]
                best_extent = best_selected_files[seq]["structure_extent"]
                replace = False
                relative_extent = structure_extent * curr_spac[2]
                if relative_extent >= (best_extent * best_spac[2]):  # and min(curr_dim) < min(best_dim):
                    if relative_extent == (best_extent * best_spac[2]) and curr_spac[2] < best_spac[2]:
                        replace = True
                    elif relative_extent > (best_extent * best_spac[2]):
                        replace = True

                if replace:
                    best_selected_files[seq] = {"file": nf, "spacings": nf_nib.header.get_zooms(), "dims": nf_nib.shape,
                                                "structure_extent": structure_extent}
        except Exception as e:
            logging.error(f"Assessing CT scan selection status failed with {e}")
            continue

    # If still empty, loosening the requirements on the eligible inputs
    if best_selected_files["HR"] is None:
        exclusion_list.remove("derived")
        exclusion_list.remove("secondary")
        seq = "HR"
        for nf in all_files_info.keys():
            name_split = os.path.basename(nf).lower().split('_')
            if any(item in name_split for item in exclusion_list):
                logging.info(f"Discarded input CT scan {nf} because its name contains an exclusion tag")
                continue

            if best_selected_files[seq] is None:
                best_selected_files[seq] = all_files_info[nf]
            else:
                best_spac = best_selected_files[seq]["spacings"]
                best_dim = best_selected_files[seq]["dims"]
                best_extent = best_selected_files[seq]["structure_extent"]
                replace = False
                relative_extent = all_files_info[nf]["structure_extent"] * all_files_info[nf]["spacings"][2]
                if relative_extent > (best_extent * best_spac[2]): # and min(curr_dim) < min(best_dim):
                    replace = True

                if replace:
                    best_selected_files[seq] = all_files_info[nf]
    # Saving the selection info
    try:
        dict_non_empty = True in [best_selected_files[x] is not None for x in best_selected_files.keys()]
        if dict_non_empty:
            pd.DataFrame([[key, value["file"]] for key, value in best_selected_files.items() if value is not None],
                         columns=["Sequence", "file"]).to_csv(dest_filename, index=False)
    except Exception as e:
        logging.error(f"Writing the selection info to csv failed with {e}")
