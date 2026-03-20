import os
import shutil
import glob
import nibabel as nib
import numpy as np
import logging
import re
from pathlib import Path

import pandas as pd

from .classification import compute_classification
from ...Utils.image_utils import is_image_eligible
from ...Utils.utils import normalize, penalized_score, signed_size_score, slice_thickness_score


def identify_sequences(input_folder: str, override: bool = False) -> None:
    """
    Runs the sequence classification model over each converted image inside the DICOM-conv for the input patient.
    The image name is appended with the sequence acronym, in addition to the csv file with the classification probabilities
    in case of uncertainties.
    OBS: some sequences are not included in the classification model, only the following are handled: [T1-w, T1-CE, T2, FLAIR]
    """
    output_root = input_folder

    nifti_files = glob.glob(os.path.join(output_root, "**/*.nii.gz"), recursive=False)
    for nf in nifti_files:
        try:
            compute_classification(nf, target_name="sequence", override=override)
        except Exception as e:
            logging.warning(f"Sequence classification on {nf} failed with {e}")
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
    Identifying the best MR scan for each of the main sequences (i.e., T1c, T1w, FLAIR, T2), focusing primarily on
    the original and primary acquisitions.
    """
    exclusion_list = ["diffusion", "adc", "dwi", "localizer", "screensave", "tractography", "perfusion", "projection"]

    dest_filename = os.path.join(input_folder, "selection.csv")
    if os.path.exists(dest_filename) and not override:
        logging.info(f"Skipping sequence selection step, already performed in {input_folder}")
        return

    main_sequence_types = ["T1-CE", "T1-w", "FLAIR", "T2"]
    all_files_pre_seq = dict.fromkeys(main_sequence_types, None)
    best_selected_files = dict.fromkeys(main_sequence_types, None)
    for s in main_sequence_types:
        try:
            nifti_files = [f for f in Path(input_folder).glob('*.nii.gz') if s in os.path.basename(f)]
            # Collecting relevant metadata for each eligible scan for the given sequence
            for nf in nifti_files:
                nf = str(nf)
                if any(item in os.path.basename(nf).lower() for item in exclusion_list):
                    logging.info(f"Discarded input MR scan {nf} because its name contains an exclusion tag")
                    continue
                nf_nib = nib.load(nf)
                if not is_image_eligible(image=nf_nib):
                    logging.info(f"Discarded input MR scan {nf} because the image is not eligible")
                    continue
                seq = os.path.basename(nf).split('_Seq-')[1].split('_')[0]
                if seq not in main_sequence_types:
                    seq = None
                    probability = None
                else:
                    probability = int(re.findall(r'-?\d*\.?\d+', os.path.basename(nf).split('_Seq-')[1].split('_')[1])[0])

                original_volume = True
                if any(item in os.path.basename(nf).lower() for item in ["secondary", "derived"]):
                    original_volume = False

                slice_thickness = nf_nib.header.get_zooms()[2]
                inplane_mm = nf_nib.header.get_zooms()[0] * nf_nib.header.get_zooms()[1]
                voxel_size = np.prod(nf_nib.header.get_zooms())
                anisotropy = max(nf_nib.header.get_zooms()) / min(nf_nib.header.get_zooms())
                disk_size = os.path.getsize(nf) / (1024*1024)
                vol_orientation = nib.orientations.aff2axcodes(nf_nib.affine)
                primary_orientation = "Axial"
                if slice_thickness > 2 and vol_orientation[2] in ["S", "I"]:
                    primary_orientation = "Axial"
                elif slice_thickness > 2 and vol_orientation[2] in ["A", "P"]:
                    primary_orientation = "Coronal"
                elif slice_thickness > 2 and vol_orientation[2] in ["R", "L"]:
                    primary_orientation = "Sagittal"
                is_axial = primary_orientation == "Axial"
                volume_info = [s, os.path.basename(nf), original_volume, voxel_size, inplane_mm, slice_thickness, anisotropy,
                               probability, disk_size, primary_orientation, is_axial]
                if all_files_pre_seq[s] is None:
                    all_files_pre_seq[s] = [volume_info]
                else:
                    all_files_pre_seq[s].append(volume_info)
            all_files_info_df = pd.DataFrame(all_files_pre_seq[s],
                                             columns=["sequence", "file", "original_volume", "voxel_size", "inplane",
                                                      "slice_thickness", "anisotropy", "probability", "disk_size",
                                                      "orientation", "is_axial"])
            """
            Identifying the best scan for each sequence:
              * Primary acquisition (original/primary before derived/secondary) 
            """
            sort_by = [
                ("original_volume", False),  # True first
                ("slice_thickness", True),  # asc
                ("disk_size", False),  # desc
                ("is_axial", False),  # True first
                ("probability", False),  # desc
                ("voxel_size", True),  # asc
                ("anisotropy", True),  # asc (more isotropic first)
                ("inplane", True),  # asc
            ]

            by, ascending = zip(*sort_by)
            sort_df = all_files_info_df.sort_values(list(by), ascending=list(ascending), kind="mergesort")
            score_df = compute_score(sort_df, sequence=s)
            if len(score_df) != 0:
                best_selected_files[s] = score_df.iloc[0]["file"]
        except Exception as e:
            logging.error(f"Assessing MR scan selection status failed with {e}")
            pass

    side_sequence_types = ["DWI", "ADC"]
    all_files_pre_seq = dict.fromkeys(side_sequence_types, None)
    best_selected_files.update(dict.fromkeys(side_sequence_types, None))
    inclusion_list = ["diffusion", "adc", "dwi", "tractography", "perfusion", "trace", "tracew"]
    nifti_files = [f for f in Path(input_folder).glob('*.nii.gz') if any(item.lower() in os.path.basename(f).lower() for item in inclusion_list)]
    for nf in nifti_files:
        nf = str(nf)
        if "adc" in os.path.basename(nf).lower():
            best_selected_files["ADC"] = os.path.basename(nf)
        elif any(v in os.path.basename(nf).lower() for v in ["diffusion", "trace", "tracew"]):
            best_selected_files["DWI"] = os.path.basename(nf)

    # Saving the selection info
    try:
        pd.DataFrame([[key, value] for key, value in best_selected_files.items() if value is not None],
                     columns=["Sequence", "file"]).to_csv(dest_filename, index=False)
    except Exception as e:
        logging.error(f"Writing the selection info to csv failed with {e}")


def compute_score(df, sequence):
    """
    Not a single MR scan metadata is enough to assess which is the best scan for a given sequence, hence a weighted
    sorting across the major metadata is put in place.
    Importance: original volume, size on disk, slice thickness (3rd axis), axial view, sequence classification probability
    @TODO. Should there be a different weighting strategy for each MR sequence?
    """
    df = df.copy()

    if len(df) == 0:
        logging.info("Skipping score computation, DataFrame is empty.")
        return df

    df["n_voxel_size"] = 1 - normalize(df["voxel_size"])
    df["n_inplane"]      = 1 - normalize(df["inplane"])
    df["n_thickness"]    = slice_thickness_score(df["slice_thickness"], ideal=0.5, max_acceptable=6.) #1 - normalize(df["slice_thickness"])
    df["n_anisotropy"]   = 1 - normalize(df["anisotropy"])
    df["n_prob"]         = penalized_score(df["probability"], threshold=90)
    df["n_disk_size"]     = signed_size_score(df["disk_size"], min_ok=1., max_ok=10) if sequence != "T1-CE" else signed_size_score(df["disk_size"], min_ok=3., max_ok=50.)


    df["score"] = (
        0.00 * df["n_voxel_size"]
        + 0.00 * df["n_inplane"]
        + 0.20 * df["n_thickness"]
        + 0.00 * df["n_anisotropy"]
        + 0.35 * df["original_volume"].astype(float)
        + 0.10 * df["is_axial"].astype(float)
        + 0.20 * df["n_prob"]
        + 0.20 * df["n_disk_size"]
    )


    return df.sort_values("score", ascending=False)

