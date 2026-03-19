import re
import SimpleITK as sitk

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