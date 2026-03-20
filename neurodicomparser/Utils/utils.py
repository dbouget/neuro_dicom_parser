from sklearn.preprocessing import MinMaxScaler
import numpy as np
import os


def normalize(series):
    arr = np.array(series).reshape(-1, 1)
    return MinMaxScaler().fit_transform(arr).ravel()


def penalized_score(series, threshold=75, penalty_power=3):
    """
    Score values in [0,100] with heavy penalty below threshold.

    Above threshold:
        score = value / 100

    Below threshold:
        drops rapidly toward 0 (or negative if desired)

    Args:
        series: iterable of values in [0,100]
        threshold: penalty starts below this value
        penalty_power: higher = harsher punishment

    Returns:
        np.ndarray of scores
    """
    arr = np.array(series, dtype=float)

    scores = np.empty_like(arr)

    # Above threshold → linear scaling
    above = arr >= threshold
    scores[above] = arr[above] / 100.0

    # Below threshold → heavy nonlinear penalty
    below = ~above
    scores[below] = (arr[below] / threshold) ** penalty_power * (threshold / 100.0)

    return scores

def signed_size_score(
    sizes_mb,
    min_ok=1,
    max_ok=20,
    penalty_power=1.5
):
    """
    Signed score for MR scan file sizes.

    Positive inside valid range (bigger = better)
    Negative outside range (farther = worse)

    Returns values roughly in [-1, 1]
    """
    s = np.array(sizes_mb, dtype=float)
    scores = np.zeros_like(s)

    # --- Inside range ---
    inside = (s >= min_ok) & (s <= max_ok)
    scores[inside] = (s[inside] - min_ok) / (max_ok - min_ok)

    # --- Too small ---
    small = s < min_ok
    scores[small] = -((min_ok - s[small]) / min_ok) ** penalty_power

    # --- Too large ---
    large = s > max_ok
    scores[large] = -((s[large] - max_ok) / max_ok) ** penalty_power

    return scores

def slice_thickness_score(
    thickness_mm,
    ideal=0.5,
    max_acceptable=6,
    penalty_power=1.5
):
    """
    Signed score for 3D MRI slice thickness.

    Higher score = better resolution
    Negative score = too thick slices

    Args:
        thickness_mm: iterable of slice thickness in mm
        ideal: best slice thickness (maximum score)
        max_acceptable: thickness above which score becomes negative
        penalty_power: controls steepness of penalty outside acceptable range

    Returns:
        np.ndarray of signed scores
    """
    t = np.array(thickness_mm, dtype=float)
    scores = np.zeros_like(t)

    # --- Ideal to max_acceptable: decreasing linear ---
    inside = (t >= ideal) & (t <= max_acceptable)
    scores[inside] = 1 - ((t[inside] - ideal) / (max_acceptable - ideal))

    # --- Too thick: negative penalty ---
    too_thick = t > max_acceptable
    scores[too_thick] = -((t[too_thick] - max_acceptable) / max_acceptable) ** penalty_power

    # --- Optional: slice thinner than ideal → slightly penalized or clipped ---
    too_thin = t < ideal
    # Option 1: keep at 1 (no penalty for thinner slices)
    scores[too_thin] = 1.0
    # Option 2: penalize unrealistic extremely thin slices
    # scores[too_thin] = -((ideal - t[too_thin]) / ideal) ** penalty_power

    return scores


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