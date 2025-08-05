import os
import shutil
import glob
import nibabel as nib
from ..Processing.classification import compute_classification


def identify_sequences(input_folder: str) -> None:
    """
    Runs the sequence classification model over each converted image inside the DICOM-conv for the input patient.
    The image name is appended with the sequence acronym, in addition to the csv file with the classification probabilities
    in case of uncertainties.
    OBS: some sequences are not included in the classification model, only the following are handled: [T1-w, T1-CE, T2, FLAIR]
    """
    output_root = os.path.join(input_folder, 'DICOM-conv')
    if not os.path.exists(output_root):
        print(f"The DICOM folder with converted images does not exist at {output_root}")
        return

    nifti_files = glob.glob(os.path.join(output_root, "**/*.nii.gz"), recursive=True)
    for nf in nifti_files:
        try:
            compute_classification(nf, target_name="sequence", override=False)
        except Exception as e:
            print(f"Collected {e}")
            continue


def sequence_selection(input_folder: str) -> None:
    """

    """
    exclusion_list = ["diffusion", "adc", "dwi"]
    output_conv = os.path.join(input_folder, 'DICOM-conv')
    output_sel = os.path.join(input_folder, 'NIFTI-selection')
    if not os.path.exists(output_conv):
        print(f"The folder with converted images does not exist at {output_conv}")
        return
    if os.path.exists(output_sel):
        shutil.rmtree(output_sel)
    os.makedirs(output_sel)

    inv_dirs = []
    for _, dirs, _ in os.walk(output_conv):
        for d in dirs:
            inv_dirs.append(d)
        break

    for d in inv_dirs:
        curr_input_path = os.path.join(output_conv, d)
        best_selected_files = {}
        best_selected_files["T1-w"] = None
        best_selected_files["T1-CE"] = None
        best_selected_files["T2"] = None
        best_selected_files["FLAIR"] = None
        nifti_files = glob.glob(os.path.join(curr_input_path, "*.nii.gz"), recursive=False)
        for nf in nifti_files:
            try:
                name_split = os.path.basename(nf).lower().split('-')
                if any(item in name_split for item in exclusion_list):
                    continue
                nf_nib = nib.load(nf)
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
                        best_selected_files[seq] = {"file": nf, "spacings": nf_nib.header.get_zooms(),
                                                       "dims": nf_nib.shape}
            except Exception as e:
                print(f"Collected {e}")
                continue

        # Saving the selection to another folder
        for s in ["T1-w", "T1-CE", "T2", "FLAIR"]:
            if best_selected_files[s] is not None:
                src_fn = best_selected_files[s]["file"]
                dst_fn = os.path.join(output_sel, d, os.path.basename(src_fn))
                os.makedirs(os.path.dirname(dst_fn), exist_ok=True)
                shutil.copyfile(src=src_fn, dst=dst_fn)