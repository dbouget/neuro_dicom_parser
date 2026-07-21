import highdicom as hd
import numpy as np
import nibabel as nib
import pydicom
from pathlib import Path


# def convert_dicom_pair_to_nifti(image_dicom_dir: Path | str, seg_dcm_path: Path | str, output_image_path: Path | str, 
#                                 output_mask_path: Path | str):
#     """
#     Simultaneous conversion of a DICOM input and DICOM segmentation to Nifti files.
#     """
#     if isinstance(image_dicom_dir, str):
#         image_dicom_dir = Path(image_dicom_dir)

#     # --- Step 1: Load source image series ---
#     source_dcm_files = sorted(image_dicom_dir.glob("*.dcm"))
#     if not source_dcm_files:
#         raise FileNotFoundError(f"No .dcm files in {image_dicom_dir}")

#     source_datasets = load_image_series(image_dicom_dir)
#     source_volume = hd.get_volume_from_series(source_datasets)
#     # print(f"Source spatial shape : {source_volume.spatial_shape}")

#     # --- Step 2: Load and reconstruct SEG ---
#     seg = hd.seg.segread(str(seg_dcm_path))
#     # print(f"Num segments         : {seg.number_of_segments}")

#     seg_volume = seg.get_volume(combine_segments=True, relabel=False)
#     # print(f"Seg spatial shape    : {seg_volume.spatial_shape}")

#     # --- Step 3: Match SEG geometry to source ---
#     seg_volume_matched = seg_volume.match_geometry(source_volume)
#     # print(f"Matched spatial shape: {seg_volume_matched.spatial_shape}")

#     if seg_volume_matched.spatial_shape != source_volume.spatial_shape:
#         raise ValueError(
#             f"Shape mismatch after match_geometry — "
#             f"seg={seg_volume_matched.spatial_shape}, "
#             f"source={source_volume.spatial_shape}. "
#             f"Resampling required (e.g. with SimpleITK)."
#         )

#     # --- Step 4: Save both using identical pipeline ---
#     # Both go through get_affine('RAS') with no transpose.
#     # Since both volumes come from highdicom with the same axis convention,
#     # the resulting NIfTI files are guaranteed to have matching
#     # shape, affine, spacing and orientation.
#     shared_affine = source_volume.get_affine('RAS')

#     image_nifti = nib.Nifti1Image(
#         source_volume.array.astype(np.float32),
#         affine=shared_affine,
#     )
#     nib.save(image_nifti, str(output_image_path))
#     # print(f"Saved image          : {output_image_path}")
#     # print(f"Image shape          : {image_nifti.shape}")

#     mask_nifti = nib.Nifti1Image(
#         seg_volume_matched.array.astype(np.uint8),
#         affine=shared_affine,
#     )
#     nib.save(mask_nifti, str(output_mask_path))
#     # print(f"Saved mask           : {output_mask_path}")
#     # print(f"Mask shape           : {mask_nifti.shape}")
#     # print(f"Unique mask values   : {np.unique(seg_volume_matched.array)}")

#     # Sanity checks
#     assert image_nifti.shape == mask_nifti.shape, "Shape mismatch"
#     assert np.allclose(image_nifti.affine, mask_nifti.affine), "Affine mismatch"
#     # print("Shape and affine match confirmed.")

import highdicom as hd
import numpy as np
import nibabel as nib
import pydicom
import SimpleITK as sitk
import tempfile
from pathlib import Path


def convert_dicom_pair_to_nifti(image_dicom_dir: Path | str, seg_dcm_path: Path | str, output_image_path: Path | str,
                                output_mask_path: Path | str):
    """
    Simultaneous conversion of a DICOM input and DICOM segmentation to Nifti files.
    """
    if isinstance(image_dicom_dir, str):
        image_dicom_dir = Path(image_dicom_dir)

    # --- Step 1: Load source image series ---
    source_datasets = load_image_series(image_dicom_dir)
    source_volume = hd.get_volume_from_series(source_datasets)
    # print(f"Source spatial shape : {source_volume.spatial_shape}")

    # --- Step 2: Load SEG ---
    seg = hd.seg.segread(str(seg_dcm_path))
    seg_volume = seg.get_volume(combine_segments=True, relabel=False)
    # print(f"Seg spatial shape    : {seg_volume.spatial_shape}")

    # --- Step 3: Write both to temp NIfTI files ---
    # Highdicom -> nibabel -> disk -> SimpleITK
    # This lets each library handle its own conventions correctly,
    # avoiding manual affine/direction matrix construction entirely.
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_image_path = Path(tmp_dir) / "image.nii.gz"
        tmp_mask_path  = Path(tmp_dir) / "mask.nii.gz"

        # Save image NIfTI via highdicom's get_affine('RAS')
        nib.save(
            nib.Nifti1Image(
                source_volume.array.astype(np.float32),
                affine=source_volume.get_affine('RAS'),
            ),
            str(tmp_image_path),
        )

        # Save raw seg NIfTI (before resampling)
        nib.save(
            nib.Nifti1Image(
                seg_volume.array.astype(np.uint8),
                affine=seg_volume.get_affine('RAS'),
            ),
            str(tmp_mask_path),
        )

        # --- Step 4: Load both into SimpleITK ---
        # SimpleITK reads NIfTI natively and handles RAS/LPS internally
        sitk_image = sitk.ReadImage(str(tmp_image_path), sitk.sitkFloat32)
        sitk_mask  = sitk.ReadImage(str(tmp_mask_path),  sitk.sitkUInt8)

        # print(f"sitk image size    : {sitk_image.GetSize()}")
        # print(f"sitk mask size     : {sitk_mask.GetSize()}")

        # --- Step 5: Resample mask onto image grid ---
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(sitk_image)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        resampler.SetOutputPixelType(sitk.sitkUInt8)
        sitk_mask_resampled = resampler.Execute(sitk_mask)

        # print(f"Resampled mask size: {sitk_mask_resampled.GetSize()}")

        # --- Step 6: Write final outputs directly via SimpleITK ---
        # Write image
        sitk.WriteImage(sitk_image, str(output_image_path))
        # Write resampled mask
        sitk.WriteImage(sitk_mask_resampled, str(output_mask_path))

    # --- Step 7: Verify ---
    img  = nib.load(str(output_image_path))
    mask = nib.load(str(output_mask_path))
    # print(f"Final image shape  : {img.shape}")
    # print(f"Final mask shape   : {mask.shape}")
    # print(f"Shapes match       : {img.shape == mask.shape}")
    # print(f"Affines match      : {np.allclose(img.affine, mask.affine, atol=1e-3)}")
    # print(f"Unique mask values : {np.unique(mask.get_fdata())}")

def load_image_series(dicom_dir: Path) -> list:
    """Load only proper image slices, filtering out non-image DICOM objects."""
    datasets = []
    for f in sorted(dicom_dir.glob("*.dcm")):
        try:
            ds = pydicom.dcmread(str(f))
            # Only keep files that have the attributes needed for a volume:
            # ImageOrientationPatient and ImagePositionPatient are mandatory
            # for spatial reconstruction. PixelData ensures it's an image.
            if (
                hasattr(ds, 'ImageOrientationPatient')
                and hasattr(ds, 'ImagePositionPatient')
                and hasattr(ds, 'PixelData')
            ):
                datasets.append(ds)
            else:
                print(f"Skipping non-image file: {f.name} "
                      f"(SOPClassUID={getattr(ds, 'SOPClassUID', 'unknown')})")
        except Exception as e:
            print(f"Skipping unreadable file: {f.name} ({e})")

    if not datasets:
        raise FileNotFoundError(f"No valid image slices found in {dicom_dir}")

    # print(f"Loaded {len(datasets)} image slices from {dicom_dir}")
    return datasets