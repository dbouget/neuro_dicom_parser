# Utility tool for DICOM folder conversion to Nifti

Code for processing a patient DICOM folder retrieved from the PACS system for a patient referred to a neuroradiology
or neurosurgery department. All DICOM acquisitions are converted to nifti, the corresponding MR sequences are 
identified for each scan, and then a subset of four MR scans (i.e., T1w, T1w-CE, T2, FLAIR) is isolated for further
processing.

## [Installation](https://github.com/dbouget/neuro_dicom_parser#installation)

```
pip install git+https://github.com/dbouget/neuro_dicom_parser.git
```

## [Getting started](https://github.com/dbouget/neuro_dicom_parser#getting-started)

### [CLI](https://github.com/dbouget/neuro_dicom_parser#cli)

If the input is a folder for a single patient
```
neurodicomparser -i "/path/to/single_input_folder" -o "/path/to/destination_folder" (-v debug)
```

If the input is a folder for multiple patients
```
neurodicomparser -f "/path/to/cohort_input_folder" -o "/path/to/destination_folder" (-v debug)
```

### [Python module](https://github.com/dbouget/neuro_dicom_parser#python-module)

```
from neurodicomparser.run import run_cohort, run_single
run_single(input_folder="/path/to/single_input_folder", output_folder="/path/to/destination_folder")
run_cohort(input_folder="/path/to/cohort_input_folder", output_folder="/path/to/destination_folder")
```

