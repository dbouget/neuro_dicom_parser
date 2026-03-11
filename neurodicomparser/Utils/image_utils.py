import nibabel as nib

def is_image_eligible(image: nib.Nifti1Image) -> bool:
    """

    """
    res = True
    spacings = image.header.get_zooms()[0:3]
    dimensions = image.shape[0:3]

    if min(dimensions) <= 15:
        res = False
    if len(image.header.get_zooms()) == 4:
        res = False

    return res