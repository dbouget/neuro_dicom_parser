import logging
import pydicom
import os
import numpy as np
import shutil
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.pixel_data_handlers.util import apply_modality_lut
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from ...Utils.io_utils import sanitize_filename


def reconstruct_raw_dicom(input_folder: str | os.PathLike, dest_folder: str | os.PathLike) -> str | os.PathLike:
    """

    For a fully anonymised DICOM folder, where even the InstanceSeriesUIDs have been randomized, the ordering of each dcm file has to 
    be identified and proper UIDs generated.

    :param input_folder:
    :param dest_folder:
    :return:
    """
    try:
        # --- 1. Read all DICOM slices ---
        slices = []
        for fname in os.listdir(input_folder):
            path = os.path.join(input_folder, fname)
            if not os.path.isfile(path):
                continue
            try:
                ds = pydicom.dcmread(path)

                # Enable GDCM or pylibjpeg pixel handlers
                pixel_array = ds.pixel_array  # Now it should decode
                # pixel_array = apply_modality_lut(pixel_array, ds)  # optional, for CT scaling
                if hasattr(ds, "PixelData"):
                    slices.append(ds)
            except Exception as e:
                err_msg = " DICOM is encrypted with a private Sectra Compression format" if "1.2.752.24.3.7.6" in e.args[0] else ""
                raise ValueError(f"Reading PixelData for elements in {input_folder} failed with {e}." + err_msg)

        if len(slices) == 0:
            raise RuntimeError("No slices with PixelData found")

        sequence_readable_name = None
        try:
            sequence_readable_name = os.path.basename(input_folder) + '_' + '_'.join(slices[0]["ImageType"])
            if hasattr(slices[0], "SeriesDescription"):
                sequence_readable_name = sequence_readable_name + '_' + slices[0]["SeriesDescription"].value
            if hasattr(slices[0], "PerformedProcedureStepDescription"):
                sequence_readable_name = sequence_readable_name + '_' + slices[0][
                "PerformedProcedureStepDescription"].value
        except Exception as e:
            sequence_readable_name = os.path.basename(input_folder)
        sequence_readable_name = sanitize_filename(sequence_readable_name)
        curr_dest_folder = os.path.join(dest_folder, sequence_readable_name)
        if os.path.exists(curr_dest_folder):
            logging.info("Already converted, skipping.")
            return curr_dest_folder

        # -------------------------------
        # 2. Compute slice normal and sort slices along it
        # -------------------------------
        iop = slices[0].ImageOrientationPatient
        row_cos = np.array(iop[:3])
        col_cos = np.array(iop[3:6])
        slice_normal = np.cross(row_cos, col_cos)

        # positions along slice normal
        positions = [np.dot(slice_normal, s.ImagePositionPatient) for s in slices]
        slices_sorted = [s for _, s in sorted(zip(positions, slices), key=lambda x: x[0])]

        # Ensure first slice is inferior
        if positions[0] > positions[-1]:
            slices_sorted = list(reversed(slices_sorted))

        # Remove potential localizer-encoded slices
        single_localizers = ["localizer" in [x.lower() for x in y.ImageType] for y in slices_sorted]
        if True in single_localizers:
            final_sorted = []
            sl_inds = [i for i, value in enumerate(single_localizers) if value == True]
            for ci, val in enumerate(slices_sorted):
                if ci not in sl_inds:
                    final_sorted.append(val)
            slices_sorted = final_sorted

        current_shapes = set([(x.Rows, x.Columns) for x in slices_sorted])
        if len(current_shapes) > 1:
            from collections import Counter
            shc = Counter([(x.Rows, x.Columns) for x in slices_sorted])
            # @ Should iterate the dict and remove slices with incorrect shapes.
        # -------------------------------
        # 3. Stack slices into 3D volume with modality LUT applied
        # -------------------------------
        try:
            volume = np.stack([apply_modality_lut(s.pixel_array, s) for s in slices_sorted], axis=-1).astype(np.int16)
        except Exception as e:
            raise ValueError(f"One or multiple slices of the volume has a different shape, to investigate. Collected {e}")

        # -------------------------------
        # 4. Build DICOM affine
        # -------------------------------
        px, py = slices[0].PixelSpacing
        pz = float(getattr(slices[0], 'SpacingBetweenSlices', slices[0].SliceThickness))
        origin = np.array(slices_sorted[0].ImagePositionPatient)

        R = np.column_stack((row_cos * px, col_cos * py, slice_normal * pz))
        affine = np.eye(4)
        affine[0:3, 0:3] = R
        affine[0:3, 3] = origin

        # -------------------------------
        # 3. Generate consistent SeriesInstanceUID
        # -------------------------------
        series_uid = generate_uid()
        study_uid = slices_sorted[0].StudyInstanceUID

        # -------------------------------
        # 5. Export reconstructed 3D DICOM series
        # -------------------------------
        if os.path.exists(curr_dest_folder):
            shutil.rmtree(curr_dest_folder)
        os.makedirs(curr_dest_folder)

        # -------------------------------
        # 4. Write individual slices
        # -------------------------------
        for idx, ds in enumerate(slices_sorted):
            # New SOPInstanceUID
            sop_uid = generate_uid()

            # File Meta
            file_meta = FileMetaDataset()
            file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
            file_meta.MediaStorageSOPInstanceUID = sop_uid
            file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

            # New FileDataset
            out_ds = FileDataset(
                os.path.join(curr_dest_folder, f"IM_{idx:04d}.dcm"),
                {}, file_meta=file_meta, preamble=b"\0" * 128
            )

            # Copy all metadata
            for elem in ds.iterall():
                try:
                    out_ds.add(elem)
                except:
                    pass  # skip read-only or problematic tags

            # Update required fields for new instance
            out_ds.SOPInstanceUID = sop_uid
            out_ds.SeriesInstanceUID = series_uid
            out_ds.StudyInstanceUID = study_uid
            out_ds.InstanceNumber = idx + 1
            out_ds.file_meta = file_meta

            # Copy PixelData exactly
            out_ds.PixelData = ds.pixel_array.tobytes() #ds.PixelData

            # Save slice
            out_ds.save_as(os.path.join(curr_dest_folder, f"IM_{idx:04d}.dcm"))
    except Exception as e:
        logging.error(f"Conversion failed for folder: {input_folder} failed with:\n {e}")
        raise ValueError(f"{e}")

    return curr_dest_folder