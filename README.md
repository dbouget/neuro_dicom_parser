# neuro_dicom_parser

> A utility tool for converting patient DICOM folders to NIfTI.

Designed for DICOM exports retrieved from PACS systems in radiology departments. Supports both SECTRA CD Media and manually-organised folder structures.

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
    - [\[Docker\]](#docker)
- [Configuration Reference](#configuration-reference)
  - [\[Case\]](#case)
  - [\[DICOM\]](#dicom)
  - [\[Identification\]](#identification)
- [Expected Folder Structures](#expected-folder-structures)
  - [SECTRA CD Media](#sectra-cd-media)
  - [Manual](#manual)
- [Examples](#examples)
- [License](#license)

---

## Requirements

- Python 3.10+
- [dcm2niix](https://github.com/rordenlab/dcm2niix) — recommended conversion backend (can also use `Simpleitk`)

---

## Installation

```bash
pip install git+https://github.com/dbouget/neuro_dicom_parser.git
```

Or clone and install locally:

```bash
git clone https://github.com/dbouget/neuro_dicom_parser.git
cd neuro_dicom_parser
pip install .
```

---

## Quick Start

1. Copy the blank config template:
   ```bash
   cp blank_user_options.ini options.ini
   ```
2. Fill in all the sections: `[Case]`, `[DICOM]` (and `[Identification]`).
3. Run:
   ```bash
   python main.py -c options.ini
   ```

> The first two sections must be filled for every run — the third one is optional.

### Docker
For launching the Docker image as a CLI, run the following, after replacing the <variables> with actual paths matching the files on your machine:  

```
docker run -v </path/to/data>:/workspace/resources -t -i --network=host --ipc=host --user $(id -u) dbouget/neurodicomparser:v1.0-py310-cpu -c /workspace/resources/config.ini -v debug
```

## Configuration Reference

The config file uses standard `.ini` format. Inline comments start with `#` and are ignored at runtime.

---

### [Case]

| Field | Required | Accepted values | Description |
|---|---|---|---|
| `input_folder` | ✅ | path | Full path to the folder to process |
| `output_folder` | ✅ | path | Full path to the base directory where results will be stored |
| `content_granularity` | ✅ | `cohort`, `patient`, `timepoint`, `image` | Granularity of content inside the input folder |

> **`content_granularity` note:** Use `cohort` when the input folder contains multiple patient subfolders. Use `patient` when pointing directly at one patient's folder. Use `timepoint` or `image` for finer-grained inputs targeting a single visit or single acquisition respectively.

---

### [DICOM]

| Field | Required | Accepted values | Description |
|---|---|---|---|
| `override_existing` | ✅ | `true`, `false` | Whether to redo and overwrite any previous conversion already present in the output folder |
| `structure` | ✅ | `sectra_cdmedia`, `manual` | The on-disk organisation of the DICOM folders — see [Expected Folder Structures](#expected-folder-structures) |
| `conversion_method` | ✅ | `dcm2niix` | Backend used for DICOM→NIfTI conversion |
| `fully_anonymised` | ✅ | `true`, `false` | Whether the DICOM export performed complete anonymisation, including DICOM Instance/Series UID tags |

> **`fully_anonymised` note:** Set to `true` only if the PACS export anonymised the UID tags. Incorrect values here may cause series matching to fail silently.

---

### [Identification]

| Field | Required | Accepted values | Description |
|---|---|---|---|
| `domain` | ✅ | `neuro`, `mediastinum` | Clinical domain of the DICOM content, used to select the appropriate sequence classifier |
| `perform` | ✅ | `true`, `false` | Whether to run sequence identification and best-sequence selection after conversion |
| `override_classification` | ✅ | `true`, `false` | Whether to rerun and overwrite any previous sequence classification results |
| `override_selection` | ✅ | `true`, `false` | Whether to rerun and overwrite any previous best-sequence selection results |

> **`perform=false` note:** If set to `false`, the tool will only perform DICOM→NIfTI conversion and skip all sequence identification steps. `override_classification` and `override_selection` are ignored in that case.

## Expected Folder Structures

Two input folder structures are currently supported. Choose the one matching your `structure` value in `[DICOM]`.

### SECTRA CD Media

For DICOM folders exported from PACS as SECTRA CD Media:

```
└── path/to/input/
    └── patient1/
        ├── CDViewer.zip
        ├── run_cdviewer.exe
        ├── DICOMDIR
        └── DICOM/
            └── AB366595/
                └── 00002E47/
                    └── ACFB2931/
                        ├── 0000C3D4/
                        │   ├── *.dcm
                        │   └── [...]
                        ├── 002033D4/
                        └── [...]
```

---

### Manual

For DICOM folders organised manually:

```
└── path/to/input/
    └── patient1/
        ├── investigation1/
        │   └── dicom/
        │       ├── acquisition1/
        │       │   ├── *.dcm
        │       │   └── [...]
        │       └── acquisition2/
        │           ├── *.dcm
        │           └── [...]
        └── investigation2/
            └── dicom/
                ├── acquisition1/
                │   └── [...]
                └── acquisitionX/
                    └── [...]
```

---

## Examples

### Single patient, SECTRA CD Media, with full identification

```ini
[Case]
input_folder=/data/pacs_export/patient_001
output_folder=/data/converted/patient_001
content_granularity=patient

[DICOM]
override_existing=false
structure=sectra_cdmedia
conversion_method=dcm2niix
fully_anonymised=false

[Identification]
domain=neuro
perform=true
override_classification=false
override_selection=false
```

---

### Full cohort, manual structure, conversion only

```ini
[Case]
input_folder=/data/cohort_raw
output_folder=/data/cohort_converted
content_granularity=cohort

[DICOM]
override_existing=false
structure=manual
conversion_method=dcm2niix
fully_anonymised=true

[Identification]
domain=neuro
perform=false
override_classification=false
override_selection=false
```

---

### Re-run identification on an already-converted cohort

```ini
[Case]
input_folder=/data/cohort_raw
output_folder=/data/cohort_converted
content_granularity=cohort

[DICOM]
override_existing=false
structure=manual
conversion_method=dcm2niix
fully_anonymised=false

[Identification]
domain=neuro
perform=true
override_classification=true
override_selection=true
```

---

## License

BSD 2-Clause — see [LICENSE.md](LICENSE.md) for details.