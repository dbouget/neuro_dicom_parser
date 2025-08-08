import nibabel as nib

def is_image_eligible(image: nib.Nifti1Image) -> bool:
    """

    """
    res = True
    spacings = image.header.get_zooms()
    dimensions = image.shape

    if min(dimensions) <= 15:
        res = False

    return res