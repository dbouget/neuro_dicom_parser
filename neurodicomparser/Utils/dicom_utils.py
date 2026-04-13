import re
import os
from typing import Tuple
from collections import defaultdict
import pydicom
import SimpleITK as sitk
import pandas as pd
import shutil
import json
import subprocess
import random
import numpy as np
import pydicom
from pathlib import Path
import nibabel as nib
from ..Utils.io_utils import sanitize_filename


def is_dicom_readable(reader: pydicom.dataset) -> Tuple[bool, str]:
    syntax_uid = reader.file_meta.TransferSyntaxUID
    msg = ""
    status = True
    if syntax_uid == '1.2.752.24.3.7.7':
        status = False
        msg = "Transfer syntax issue: SECTRA proprietary"
    elif syntax_uid == '1.2.840.10008.1.2.5':
        status = False
        msg = "Transfer syntax issue: RLE Lossless (run-length encoding)"

    return status, msg

def is_dicom_acquisition_primary(reader: sitk.ImageSeriesReader | pydicom.Dataset) -> bool:
    """

    """
    result = False
    if isinstance(reader, sitk.ImageSeriesReader):
        dc_keys = reader.GetMetaDataKeys(0)
        if '0008|0008' in dc_keys:
            result = re.split(r'\\+', reader.GetMetaData(0, '0008|0008'))[0].lower() == 'original'
    elif isinstance(reader, pydicom.Dataset):
        result = reader["ImageType"][0].lower() == 'original'
    return result

def collect_dicom_metadata(input: str | os.PathLike) -> dict:
    ds = pydicom.dcmread(input, stop_before_pixels=True)

    # Build metatags dict from pydicom dataset
    metatags = {
        f"{elem.tag.group:04x}|{elem.tag.element:04x}": 
            str(elem.value).encode('utf-8', 'replace').decode('utf-8')
        for elem in ds
        if elem.keyword != 'PixelData'
    }
    return metatags

def extract_dicom_date(reader: sitk.ImageSeriesReader | pydicom.Dataset) -> str | None:
    """

    """
    if isinstance(reader, sitk.ImageSeriesReader):
        date_dctags = [
        '0008|0012',  # Instance Creation Date
        '0008|0020',  # Study Date
        '0008|0021',  # Series Date
        '0008|0022',  # Acquisition Date
        '0008|0023',  # Content Date
        ]
        dc_keys = reader.GetMetaDataKeys(0)
        date = None
        for tag in date_dctags:
            if tag not in dc_keys:
                continue

            raw_value = reader.GetMetaData(0, tag)
            if not raw_value or raw_value == "":
                continue

            date = raw_value[:8]  # YYYYMMDD
            break
    elif isinstance(reader, pydicom.Dataset):
        date_dctags = ["InstanceCreationDate", "StudyDate", "SeriesDate", "AcquisitionDate", "ContentDate"]
        # date_dctags = [
        # 0x0008, 0x0012,  # Instance Creation Date
        # 0x0008, 0x0020,  # Study Date
        # 0x0008, 0x0021,  # Series Date
        # 0x0008, 0x0022,  # Acquisition Date
        # 0x0008, 0x0023,  # Content Date
        # ]
        date = None
        for tag in date_dctags:
            if tag in reader:
                raw_value = reader[tag].value
                if not raw_value or raw_value == "":
                    continue
                date = raw_value  # YYYYMMDD
                break
    return date

def build_sequence_readable_name(metatags: dict, input_folder: str) -> str:
    """
    Build a human-readable but collision-resistant series name.
    Structure: {modality}_{series_number}_{series_description}[_{disambiguator}]
    """
    def get(tag): 
        return metatags.get(tag, '').strip()

    modality = get('0008|0060')            # CT, MR, PT — short, stable prefix
    series_number = get('0020|0011')            # scanner-assigned, unique within study
    series_desc = get('0008|103e')            # human-readable label
    sequence_name = get('0018|0024')            # pulse sequence (MR) or protocol name
    slice_thickness = get('0018|0050')           # physical disambiguator
    image_type = get('0008|0008')            # ORIGINAL\PRIMARY
    procedure_step = get('0040|0007')            # Procedure step description
    study_desc = get('0008|1030')            # Study description
    protocol_name = get('0018|1030')            # Protocol name
    #  '0018|0081', '0018|1030'


    image_type_parts = sanitize_filename(image_type)

    # Build ordered parts, skipping empty values
    parts = [series_number] + [image_type_parts] + [p for p in [modality, series_desc, sequence_name, procedure_step, study_desc, protocol_name] if p]

    # Append disambiguators only when description alone might not be enough
    if slice_thickness:
        parts.append(f"{slice_thickness}mm")

    name = '_'.join(parts) if parts else os.path.basename(input_folder)
    return sanitize_filename(name)

def make_sidecar_key(sidecar):
    iop = [round(float(v)) for v in sidecar.get("ImageOrientationPatientDICOM", [])]
    return (
        str(sidecar.get("SeriesNumber", "")).strip(),
        str(sidecar.get("SeriesDescription", "")).strip(),
        tuple(iop),
        str(sidecar.get("ConvolutionKernel", "")).strip(),
    )

def make_dicom_key(ds):
    iop = [round(float(v)) for v in ds.ImageOrientationPatient]
    return (
        str(ds.SeriesNumber).strip(),
        str(getattr(ds, "SeriesDescription", "")).strip(),
        tuple(iop),
        str(getattr(ds, "ConvolutionKernel", "")).strip(),
    )

def group_dicoms_by_composite_key(folder):
    series_map = defaultdict(list)
    for fname in os.listdir(folder):
        fpath = os.path.join(folder, fname)
        try:
            ds = pydicom.dcmread(fpath, stop_before_pixels=True)
            key = make_dicom_key(ds)
            series_map[key].append(fpath)
        except Exception:
            continue
    return series_map

def classify_dcm2niix_outputs(tmp_folder):
    """
    Groups dcm2niix output files by base stem, classifying each role.
    Returns a list of volume descriptors.
    """
    nii_files = [f for f in os.listdir(tmp_folder) if f.endswith(".nii.gz")]
    
    volumes = {}
    for nii_file in nii_files:
        # Separate derived suffixes dcm2niix appends
        DERIVED_SUFFIXES = ["_ADC", "_TRACE", "_FA", "_ColFA", "_B0"]
        
        base = nii_file.replace(".nii.gz", "")
        derived_tag = next((s for s in DERIVED_SUFFIXES if base.endswith(s)), None)
        
        if derived_tag:
            parent_stem = base[: -len(derived_tag)]
            if parent_stem in volumes:
                volumes[parent_stem]["derived"][derived_tag] = nii_file
            else:
                # Parent not yet seen, create placeholder
                volumes[parent_stem] = {"nii": None, "json": None, "derived": {derived_tag: nii_file}, "bvec": None, "bval": None}
        else:
            if base not in volumes:
                volumes[base] = {"nii": None, "json": None, "derived": {}, "bvec": None, "bval": None}
            volumes[base]["nii"] = nii_file
            volumes[base]["json"] = base + ".json" if os.path.exists(os.path.join(tmp_folder, base + ".json")) else None
            volumes[base]["bvec"] = base + ".bvec" if os.path.exists(os.path.join(tmp_folder, base + ".bvec")) else None
            volumes[base]["bval"] = base + ".bval" if os.path.exists(os.path.join(tmp_folder, base + ".bval")) else None
    
    return volumes

def execute_and_output_reader(input_folder: str, output_folder: str, timestamp: str, reader: sitk.ImageSeriesReader,
                              method: str = "dcm2nii"):
    """

    The cases of multiple outputs from dcm2niix should be better handled in the future!

    Parameters
    ----------

    """
    # Fast metadata read — no pixel loading regardless of method
    first_file = reader.GetFileNames()[0]
    ds = pydicom.dcmread(first_file, stop_before_pixels=True)

    # Build metatags dict from pydicom dataset
    metatags = {
        f"{elem.tag.group:04x}|{elem.tag.element:04x}": 
            str(elem.value).encode('utf-8', 'replace').decode('utf-8')
        for elem in ds
        if elem.keyword != 'PixelData'
    }

    # existing_dicom_keys = reader.GetMetaDataKeys(0)
    # # Prevent weird encoding from crashing the conversion process
    # metatags = [[k, str(reader.GetMetaData(0, k)).encode('utf-8', 'replace').decode('utf-8')] for k in existing_dicom_keys]
    # # metatags_df = pd.DataFrame(metatags, columns=['Tag', 'Value'])

    sequence_readable_name = None
    try:
        sequence_readable_name = build_sequence_readable_name(metatags=metatags, input_folder=input_folder)
    except Exception as e:
        sequence_readable_name = os.path.basename(input_folder)
    sequence_readable_name = sanitize_filename(sequence_readable_name)
    dump_image_path = os.path.join(output_folder, timestamp, sequence_readable_name + '.nii.gz') if timestamp is not None else os.path.join(output_folder, sequence_readable_name + '.nii.gz')

    if os.path.exists(dump_image_path):
        stem = dump_image_path.replace('.nii.gz', '')
        counter = 1
        while os.path.exists(dump_image_path):
            dump_image_path = f"{stem}_{counter}.nii.gz"
            counter += 1

    os.makedirs(os.path.dirname(dump_image_path), exist_ok=True)

    if method == 'sitk':
        image = reader.Execute()
        sitk.WriteImage(image, dump_image_path)
    elif method == 'dcm2niix':
        tmp_folder = os.path.join(os.path.dirname(dump_image_path), 'tmp')
        output_filename = os.path.join(tmp_folder, 'recon')
        if not os.path.isdir(tmp_folder):
            os.mkdir(tmp_folder)

        exec_filepath = os.path.join(os.path.dirname(__file__), "..", "MRIcroGL", "Resources", 'dcm2niix')
        try:
            subprocess.call(
                ["{exec}".format(exec=exec_filepath),
                    "-o", "{output}".format(output=os.path.dirname(output_filename)),
                    "-f", "{filename}".format(filename=os.path.basename(output_filename)),
                    "-z", "y",
                    "{input}".format(input=os.path.dirname(reader.GetFileNames()[0]))])
        except Exception:
            if os.path.isdir(tmp_folder):
                shutil.rmtree(tmp_folder)
            raise ValueError("DICOM to nifti conversion failed for folder: {}".format(input_folder))

        series_map = group_dicoms_by_composite_key(os.path.dirname(reader.GetFileNames()[0]))
        volumes = classify_dcm2niix_outputs(tmp_folder)

        for stem, vol in volumes.items():
            try:
                if vol["nii"] is None or vol["json"] is None:
                    continue  # skip derived-only entries with no parent found

                with open(os.path.join(tmp_folder, vol["json"])) as f:
                    sidecar = json.load(f)

                # DICOM tag lookup only on the primary volume
                key = make_sidecar_key(sidecar)
                source_files = series_map.get(key, [])

                if not source_files:
                    print(f"Warning: no DICOMs matched for {stem}")
                    continue

                metatags = collect_dicom_metadata(input=source_files[0])
                # # Derive a per-volume output path from the stem suffix dcm2niix appended
                # # e.g. "recon_e1", "recon_e2" → append that suffix to the base dump path
                # base = dump_image_path.replace('.nii.gz', '')
                # stem_suffix = stem.replace('recon', '')  # e.g. "", "_e1", "_e2"
                # vol_dump_path = f"{base}{stem_suffix}.nii.gz"
                sequence_readable_name = build_sequence_readable_name(metatags=metatags, input_folder=input_folder)
                sequence_readable_name = sanitize_filename(sequence_readable_name)
                vol_dump_path = os.path.join(output_folder, timestamp, sequence_readable_name + '.nii.gz') if timestamp is not None else os.path.join(output_folder, sequence_readable_name + '.nii.gz')
                base = vol_dump_path.replace('.nii.gz', '')
                extra_dump = True
                output_filename = os.path.join(tmp_folder, vol["nii"])
                # Handle collision
                if os.path.exists(vol_dump_path):
                    if Path(vol_dump_path).stat().st_size == Path(output_filename).stat().st_size:
                        if np.sum(nib.load(vol_dump_path).get_fdata()[:] - nib.load(output_filename).get_fdata()[:]) == 0:
                            extra_dump = False
                    counter = 1
                    while os.path.exists(vol_dump_path):
                        vol_dump_path = f"{base}_{counter}.nii.gz"
                        if os.path.exists(vol_dump_path) and Path(vol_dump_path).stat().st_size == Path(output_filename).stat().st_size:
                            if np.allclose(nib.load(vol_dump_path).get_fdata()[:], nib.load(output_filename).get_fdata()[:]):
                                extra_dump = False
                                break
                        counter += 1
                if extra_dump:
                    shutil.move(src=output_filename, dst=vol_dump_path)

                meta_dump_path = os.path.join(os.path.dirname(vol_dump_path), 'Meta',
                                                os.path.basename(vol_dump_path).split('.')[0] + '_metadata.csv')
                os.makedirs(os.path.dirname(meta_dump_path), exist_ok=True)
                pd.DataFrame(list(metatags.items()), columns=['Tag', 'Value']).to_csv(meta_dump_path, index=False, encoding='utf-8')
            except Exception as e:
                raise

            # Can be infered afterwards anyways if needed from the saved image
            # for dv in vol["derived"]:
            #     derived_dst_folder = os.path.join(os.path.dirname(dump_image_path), "derived", os.path.basename(dump_image_path).replace('.nii.gz', ''))
            #     os.makedirs(derived_dst_folder, exist_ok=True)
            #     for dvk in list(dv.keys()):
            #         shutil.move(src=os.path.join(tmp_folder, vol["derived"][dvk]), dst=os.path.join(derived_dst_folder, os.path.basename(dump_image_path).replace('.nii.gz', '') + dvk + '.nii.gz'))
        if os.path.isdir(tmp_folder):
            shutil.rmtree(tmp_folder)