# Utility tool for DICOM folder conversion to Nifti

Code for processing a patient DICOM folder retrieved from the PACS system for a patient referred to a neuroradiology
or neurosurgery department. All DICOM acquisitions are converted to nifti, the corresponding MR sequences are 
identified for each scan, and then a subset of four MR scans (i.e., T1w, T1w-CE, T2, FLAIR) is isolated for further
processing.

## [Installation](https://github.com/dbouget/neuro_dicom_parser#installation)

```
pip install git+https://github.com/dbouget/neuro_dicom_parser.git
```

<details>
<summary>

## [Getting started](https://github.com/dbouget/neuro_dicom_parser#getting-started)
</summary>

Different use-cases are handled based on the content to convert and the way files are stored locally. More detailed 
descriptions of folder structures for each use-case are provided below. The variables are:  
* -i (input_folder): path to the folder to process.
* -c (input_category): granularity level of the input folder content within [cohort_patient, single_patient, single_timepoint, single_image]
* -s (input_structure): indication of the way the DICOM folders are structured on disk, to select from [sectra_cdmedia, manual]
* -o (output_folder): path to the folder where the results will be stored
* -v (verbose): amount of details to be printed in the console, to select from [debug, info, warning, error]
* -x (override): if content already existing should be removed and produced again

### [CLI](https://github.com/dbouget/neuro_dicom_parser#cli)

If the input is a folder for a single patient in SECTRA CD Media structure
```
neurodicomparser -i "/path/to/patient_folder" -c single_patient -s sectra_cdmedia -o "/path/to/destination_folder" (-v debug)
```

If the input is a folder for multiple patients with manual structure
```
neurodicomparser -i "/path/to/cohort_folder" -c cohort_patient -s manual -o "/path/to/destination_folder" (-v debug)
```
</details>

### [Python module](https://github.com/dbouget/neuro_dicom_parser#python-module)

```
from neurodicomparser.run import run_cohort, run_single
run_single(input_folder="/path/to/single_input_folder", output_folder="/path/to/destination_folder")
run_cohort(input_folder="/path/to/cohort_input_folder", output_folder="/path/to/destination_folder")
```

<details>
<summary>

## [Expected folder structure](https://github.com/dbouget/neuro_dicom_parser#expected-folder-structure)
</summary>

### [Sectra CD Media](https://github.com/dbouget/neuro_dicom_parser#sectra-cd-media)
When working with DICOM folders extracted from the PACS system as CD media, the following structure is expected on disk.
The execution line would look like:  

    └── path/to/sectra-cohort/
        └── patient1/
            ├── CDViewer.zip
            ├── run_cdviewer.eze
            ├── DICOMDIR
            ├── [...]
            ├── DICOM/
            │   ├── AB366595/
            │   │   ├── 00002E47/
            │   │   │   ├── ACFB2931/
            │   │   │   │   ├── 0000C3D4/
            │   │   │   │   │   ├── *.dcm
            │   │   │   │   │   ├── [...]
            │   │   │   │   │   ├── *.dcm
            │   │   │   │   ├── 002033D4/
            │   │   │   │   ├── [...]
            │   │   │   │   └── 1E00C354/

### [Manual](https://github.com/dbouget/neuro_dicom_parser#manual)
When working with DICOM folders organized manually, the following structure is expected on disk.
The execution line would look like:  

```
neurodicomparser -i "/path/to/input_folder" -c single_patient -s manual -o "/path/to/destination_folder" (-v debug)
```

    └── path/to/manual-cohort/
        └── patient1/
            ├── investigation1/
            │   ├── dicom/
            │   │   ├── acquisition1/
            │   │   │   ├── *.dcm
            │   │   │   ├── [...]
            │   │   │   └── *.dcm
            │   │   ├── acquisition2/
            │   │   │   ├── *.dcm
            │   │   │   ├── [...]
            │   │   │   └── *.dcm
            └── investigation2/
            │   ├── dicom/
            │   │   ├── acquisition1/
            │   │   │   ├── *.dcm
            │   │   │   ├── [...]
            │   │   │   └── *.dcm
            │   │   ├── acquisition2/
            │   │   │   ├── *.dcm
            │   │   │   ├── [...]
            │   │   │   └── *.dcm
            │   │   ├── [...]
            │   │   ├── acquisitionX/
            │   │   │   ├── *.dcm
            │   │   │   ├── [...]
            │   │   │   └── *.dcm
</details>