import re
import os
from collections import defaultdict
import pydicom
import SimpleITK as sitk
import pandas as pd
import shutil
import json
import subprocess
import random
from ..Utils.io_utils import sanitize_filename


def is_dicom_acquisition_primary(reader: sitk.ImageSeriesReader) -> bool:
    """

    """
    result = False
    dc_keys = reader.GetMetaDataKeys(0)
    if '0008|0008' in dc_keys:
        result = re.split(r'\\+', reader.GetMetaData(0, '0008|0008'))[0].lower() == 'original'
    return result

def extract_dicom_date(reader: sitk.ImageSeriesReader) -> str | None:
    """

    """
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
    return date

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

def execute_and_output_reader(input_folder: str, output_folder: str, timestamp: str, reader: sitk.ImageSeriesReader, index: int = 0, method: str = "dcm2nii"):
    image = reader.Execute()
    existing_dicom_keys = reader.GetMetaDataKeys(0)
    
    # Prevent weird encoding from crashing the conversion process
    metatags = [[k, str(reader.GetMetaData(0, k)).encode('utf-8', 'replace').decode('utf-8')] for k in existing_dicom_keys]
    metatags_df = pd.DataFrame(metatags, columns=['Tag', 'Value'])
    # for k in existing_dicom_keys:
    #     v = reader.GetMetaData(0, k)
    #     print("({0}) = = \"{1}\"".format(k, v))

    sequence_readable_name = None
    try:
        sequence_readable_name = os.path.basename(input_folder) + '_' + reader.GetMetaData(0, '0008|0008')
        if '0008|103e' in metatags_df["Tag"].to_list():
            sequence_readable_name = sequence_readable_name + '_' + reader.GetMetaData(0, '0008|103e')
        if '0008|1030' in metatags_df["Tag"].to_list():
            sequence_readable_name = sequence_readable_name + '_' + reader.GetMetaData(0, '0008|1030')
        if '0018|1030' in metatags_df["Tag"].to_list():
            sequence_readable_name = sequence_readable_name + '_' + reader.GetMetaData(0, '0018|1030')
        if '0040|0007' in metatags_df["Tag"].to_list():
            sequence_readable_name = sequence_readable_name + '_' + reader.GetMetaData(0, '0040|0007')
    except Exception as e:
        sequence_readable_name = os.path.basename(input_folder)
    sequence_readable_name = sanitize_filename(sequence_readable_name)
    dump_image_path = os.path.join(output_folder, timestamp, str(index+1) + '_' + sequence_readable_name + '.nii.gz') if timestamp is not None else os.path.join(output_folder, str(index+1) + '_' + sequence_readable_name + '.nii.gz')
    if os.path.exists(dump_image_path):
        new_path = dump_image_path
        while os.path.exists(new_path):
            new_path = dump_image_path.replace('.nii.gz', f"_{random.randint(0, 100)}.nii.gz")
        dump_image_path = new_path

    os.makedirs(os.path.dirname(dump_image_path), exist_ok=True)
    if not os.path.isdir(os.path.dirname(dump_image_path)):
        os.makedirs(os.path.dirname(dump_image_path))

    if method == 'sitk':
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

        output_filename = os.path.join(tmp_folder, vol["nii"])
        shutil.move(src=output_filename, dst=dump_image_path)
        # Can be infered afterwards anyways if needed from the saved image
        # for dv in vol["derived"]:
        #     derived_dst_folder = os.path.join(os.path.dirname(dump_image_path), "derived", os.path.basename(dump_image_path).replace('.nii.gz', ''))
        #     os.makedirs(derived_dst_folder, exist_ok=True)
        #     for dvk in list(dv.keys()):
        #         shutil.move(src=os.path.join(tmp_folder, vol["derived"][dvk]), dst=os.path.join(derived_dst_folder, os.path.basename(dump_image_path).replace('.nii.gz', '') + dvk + '.nii.gz'))
        if os.path.isdir(tmp_folder):
            shutil.rmtree(tmp_folder)

        # created_filename = None
        # """
        # If/when multiple files are combined (e.g., one localizer and one scan), then multiple outputs
        # would be produced. Might be interesting to parse and save both, each with its proper name.
        # """
        # for _, _, files in os.walk(tmp_folder):
        #     for f in files:
        #         if f.split('.')[-1] == 'gz':
        #             created_filename = f
        #     break

        # if created_filename is None:
        #     if os.path.isdir(tmp_folder):
        #         shutil.rmtree(tmp_folder)
        #     continue

        # output_filename = os.path.join(tmp_folder, created_filename)
        # shutil.move(src=output_filename, dst=dump_image_path)
        # if os.path.isdir(tmp_folder):
        #     shutil.rmtree(tmp_folder)
    try:
        meta_dump_path = os.path.join(os.path.dirname(dump_image_path), 'Meta',
                                        os.path.basename(dump_image_path).split('.')[0] + '_metadata.csv')
        os.makedirs(os.path.dirname(meta_dump_path), exist_ok=True)
        metatags_df.to_csv(meta_dump_path, index=False, encoding='utf-8')
    except Exception as e:
        # Some fields in the metadata have a weird encoding....
        # metatags = [[k, str.encode(reader.GetMetaData(0, k)).decode('utf8', 'surrogateescape')] for k in
        #             existing_dicom_keys]
        raise