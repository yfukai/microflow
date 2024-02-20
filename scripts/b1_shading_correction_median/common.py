from dask import array as da
import numpy as np
from skimage import transform, filters, morphology
import ray
import fnmatch

def estimate_median_profile(images, axis, robust=False, deviation_factor=2., keepdims=True):
    if robust:
        deviation = da.abs(da.median(images, axis=axis, keepdims=True) - images)
        median_deviation = da.median(da.ravel(deviation), axis=0)
        bg = da.nanmedian(da.where(deviation < median_deviation * deviation_factor, images, np.nan), axis=axis, keepdims=keepdims)
    else:
        print(images, axis)
        bg = da.median(images, axis=axis, keepdims=keepdims)
    return bg

def scaled_filter(im2d,scale,fn,anti_aliasing=True):
    """ apply filter for scaled image and resize to original size """
    shape = im2d.shape
    im2d = np.array(im2d, dtype=np.float32)
    im2d = transform.rescale(im2d, 
        scale,
        anti_aliasing=anti_aliasing,
        preserve_range=True)
    im2d = fn(im2d)
    return transform.resize(im2d,shape,
                preserve_range=True)

def local_subtraction_2d_ignore_zero(im2d, scaling=0.1, median_disk_size=4):
    def median_filter(im):
        return filters.median(
                    im,morphology.disk(median_disk_size)
                )
    assert np.all(np.array(im2d.shape[:-2])==1)
    if np.count_nonzero(im2d) == 0:
        return im2d
    return im2d-scaled_filter(im2d, scaling, median_filter, anti_aliasing=True)

@ray.remote
def shading_correction_chunk(corrected_zarr, image, profile_zarr, ind, do_local_subtraction, 
                             mode, local_subtraction_scaling, local_subtraction_median_disk_size):
    if mode == "multiplicative":
        image = np.array((image / profile_zarr)[ind]).astype(np.float32)
    elif mode == "additive":
        image = np.array((image - profile_zarr)[ind]).astype(np.float32)
    if do_local_subtraction:
        image2 = np.empty_like(image)
        for inds in np.ndindex(image.shape[:-2]):
            image2[inds] = local_subtraction_2d_ignore_zero(
                image[inds], local_subtraction_scaling, 
                local_subtraction_median_disk_size)
        image = image2
    corrected_zarr[ind] = image

def match_pattern(pattern, string):
    return any(fnmatch.fnmatch(string, p) for p in pattern.split(", "))

pattern1 = '*DIA*'
pattern2 = '*DIA*, *EGFP*'

assert match_pattern(pattern1, "10X_Fukai_DIA_IS")  
assert not match_pattern(pattern1, "10X_Fukai_EGFP_IS")  
assert match_pattern(pattern2, "10X_Fukai_DIA_IS")  
assert match_pattern(pattern2, "10X_Fukai_EGFP_IS")  