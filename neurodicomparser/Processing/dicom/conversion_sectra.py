from collections import Counter
import os
import SimpleITK as sitk
import datetime
import time
import json
import shutil
import subprocess
import traceback
import logging
import pandas as pd
import numpy as np
from tqdm import tqdm
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.pixel_data_handlers.util import apply_modality_lut
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from ...Utils.io_utils import *
from ...Utils.OptionsConfiguration import OptionsConfiguration
from ...Utils.dicom_utils import *
from ...Processing.identification.identification_process import identification_process


def run_cohort_patient_sectra_cdmedia(input_folder: str, output_folder: str, conversion_method: str = "dcm2niix") -> None:
    """

    """
    patient_list_in_cohort = list_subdirs(input_folder)

    for patient_fn in tqdm(patient_list_in_cohort):
        run_single_patient_sectra_cdmedia(input_folder=os.path.join(input_folder, patient_fn),
                                            output_folder=output_folder, conversion_method=conversion_method)
        
def run_single_patient_sectra_cdmedia(input_folder: str, output_folder: str | None,
                                        conversion_method: str = "dcm2niix") -> None:
    """

    """
    input_folder = input_folder.rstrip(os.sep)
    converted_folder = os.path.join(output_folder, os.path.basename(input_folder)) if output_folder is not None else input_folder
    if output_folder is None:
        converted_folder = os.path.join(converted_folder, 'DICOM-conv')
    unpack_convert_dicom_folder_sectra_cdviewer(input_folder=input_folder, output_folder=converted_folder,
                                                method=conversion_method)
    identification_process(input_folder=converted_folder)

def unpack_convert_dicom_folder_sectra_cdviewer(input_folder: str, output_folder: str = None,
                                                method: str = 'dcm2niix') -> None:
    """
    Iterate over the different sub-folders of a main patient folder, and converts to nifti
    every found DICOM sequences, keeping the sub-folders structure.
    :param input_folder: folder root for a patient, expected to contain a DICOM sub-folder.
    :param method: preferred way to convert a DICOM volume to Nifti: [dcm2niix, sitk]
    :param output_folder: a DICOM-conv folder is created at the output_folder folder. This new folder will contain
     all converted volumes, along with DICOM metadata in csv files.
    """
    override = OptionsConfiguration.getInstance().dicom_override_existing
    patient_base_dicom = os.path.join(input_folder, 'DICOM')
    if not os.path.exists(patient_base_dicom):
        print('No existing DICOM folder in {}'.format(input_folder))
        return

    # Skipping patients where the conversion has already been done, unless specified otherwise
    if os.path.exists(output_folder) and not override:
        logging.info(f"Skipping DICOM to nifti conversion, output folder already exists at {output_folder}")
        return
    elif os.path.exists(output_folder) and override:
        shutil.rmtree(output_folder)
    os.makedirs(output_folder, exist_ok=True)

    main_dicom_dir = list_subdirs(patient_base_dicom)

    if len(main_dicom_dir) == 0:
        return

    for mdd in main_dicom_dir:
        patient_base_main_dicom = os.path.join(patient_base_dicom, mdd)
        timestamp_dicom_sub_dirs = list_subdirs(patient_base_main_dicom)

        # Iterating over each timestamp
        ts_order = 0
        for subdir in timestamp_dicom_sub_dirs:
            ts_order = ts_order + 1
            timestamps = []
            primary_date = None
            investigations_for_timestamp = []
            timestamp_base_main_dicom = os.path.join(patient_base_main_dicom, subdir)
            sub_dir = list_subdirs(timestamp_base_main_dicom)

            timestamp_base_main_dicom = os.path.join(timestamp_base_main_dicom, sub_dir[0])
            investigation_dirs = list_subdirs(timestamp_base_main_dicom)

            # Collecting each investigation for the current patient
            for inv in tqdm(investigation_dirs):
                try:
                    current_dicom_investigation_path = os.path.join(timestamp_base_main_dicom, inv)
                    reader = sitk.ImageSeriesReader()
                    serie_names = reader.GetGDCMSeriesIDs(current_dicom_investigation_path)

                    for s, serie in enumerate(serie_names):
                        dicom_names = reader.GetGDCMSeriesFileNames(current_dicom_investigation_path, serie)
                        reader.SetFileNames(dicom_names)
                        reader.LoadPrivateTagsOn()
                        reader.SetMetaDataDictionaryArrayUpdate(True)
                        investigations_for_timestamp.append(reader)

                        # Read metadata from ONE file only — tags are series-level, not slice-level
                        single_ds = pydicom.dcmread(dicom_names[0], stop_before_pixels=True)
                        primary = is_dicom_acquisition_primary(single_ds)
                        date = extract_dicom_date(single_ds)

                        if date:
                            timestamps.append(date)
                        if primary_date is None and primary and date is not None:
                            primary_date = date
                except Exception as e:
                    logging.error(f"Collecting metadata for {current_dicom_investigation_path} failed with {e}")
                    continue

            if len(timestamps) == 0:
                timestamp =  f"visit_{ts_order:03d}"
            elif primary_date is not None:
                timestamp = primary_date
            else:
                counts = Counter(timestamps)
                timestamp = counts.most_common(1)[0][0]
            logging.info(f'Inclusion for timestamp: {timestamp}')
            for r, reader in enumerate(investigations_for_timestamp):
                try:
                    execute_and_output_reader(input_folder=input_folder, output_folder=output_folder, 
                                              timestamp=timestamp, reader=reader, method=method)
                except Exception as e:
                    logging.error(f'Collected exception: {e}')
                    logging.error(f'{traceback.format_exc()}')
                    continue
