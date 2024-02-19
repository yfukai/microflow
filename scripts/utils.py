import numpy as np
from matplotlib import pyplot as plt
from dask import array as da
import ray
from tqdm import tqdm


def __to_iterator(obj_ids):
    while obj_ids:
        done, obj_ids = ray.wait(obj_ids)
        yield ray.get(done[0])
        
def show_ray_progress(res):
    for x in tqdm(__to_iterator(res), total=len(res)):
        pass
    return ray.get(res)

def merge_mosaic_images(images, mosaic_positions, add_mosaics = False):
    """Merge images into a mosaic image.
    
    Parameters
    ----------
    images : list of np.ndarray
        List of images to merge.
    
    mosaic_positions : list of tuple of int
        List of positions of images in the mosaic.
    
    Returns
    -------
    np.ndarray
        Mosaic image.
    """

    mosaic_positions = (mosaic_positions - np.min(mosaic_positions, axis=0)[np.newaxis]).round().astype(int)
    
    # Get the size of the mosaic image
    mosaic_size = np.max(mosaic_positions, axis=0) + np.array(images[0].shape[-2:])
    
    # Create the mosaic image
    mosaic = np.zeros(mosaic_size, dtype=images.dtype)
    
    # Merge images into the mosaic image
    for image, position in zip(images, mosaic_positions):
        mosaic[position[0]:position[0] + image.shape[0],
               position[1]:position[1] + image.shape[1]] = image
    return mosaic

def read_mosaic_image(aics_image,mosaic_dim,dimension,**kwargs):
    if mosaic_dim == "M":
        return aics_image.get_image_dask_data("M"+dimension,**kwargs)
    elif mosaic_dim == "scene":
        image_data = []
        for scene in aics_image.scenes:
            aics_image.set_scene(scene)
            image_data.append(aics_image.get_image_dask_data(dimension,**kwargs))
        return da.array(image_data)

from numcodecs import LZ4
import zarr
def open_zarr_with_synchronizer(storage_path, **kwargs):
    synchronizer = zarr.ProcessSynchronizer(str(storage_path).replace(".zarr","lock.sync"))
    default_kwargs = dict(
        mode='w',
        compressor=LZ4(),
        synchronizer=synchronizer
    )
    default_kwargs.update(kwargs)
    return zarr.open(str(storage_path), **default_kwargs)