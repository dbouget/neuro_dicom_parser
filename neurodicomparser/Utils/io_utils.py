import re


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