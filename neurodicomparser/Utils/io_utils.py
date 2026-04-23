import re
import os
import pydicom


def list_subdirs(path: str) -> list[str]:
    """
    Replace repeated os.walk+break pattern with a simple helper
    """
    return [e.name for e in os.scandir(path) if e.is_dir()]

def safename_formatting(input: str) -> str:
    """
    In case of problematic strings containing a lone surrogate: \udcb2 and more text.
    """
    cleaned_string = input.encode('utf-8', errors='ignore').decode('utf-8')
    # cleaned_string = input.encode('utf-8', errors='replace').decode('utf-8')
    return cleaned_string


def sanitize_filename(s):
    s = re.sub(r"[^A-Za-z0-9]", "_", s)  # replace special chars
    s = re.sub(r"_+", "_", s)            # collapse multiple _
    return s.strip("_")                  # remove leading/trailing _

def sanitize_to_list(value):
    """Normalize a DICOM value to a list, splitting on '\\' if needed."""
    if isinstance(value, list):
        return value
    elif isinstance(value, (list, pydicom.multival.MultiValue)):
        return [str(v).strip() for v in value]
    else:
        return [v for v in re.split(r'[^A-Za-z0-9]+', str(value).strip()) if v]
    
def next_visit_order(base_dir: str) -> int:
    """
    Scans base_dir for folders matching 'visit_NNN' and returns the next available integer.
    """
    pattern = re.compile(r"^visit_(\d{3})$")
    existing = [
        int(m.group(1))
        for name in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, name))
        and (m := pattern.match(name))
    ]
    return max(existing, default=0) + 1