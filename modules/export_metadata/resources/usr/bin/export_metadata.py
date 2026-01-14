#!/usr/bin/env python3

import pyrallis
from dataclasses import dataclass

from bioio import BioImage
import os
from os import path
import yaml
import numpy as np
from matplotlib import pyplot as plt
from get_acquired_time import frame_acquisition_times

def merge_mosaic_images(images, mosaic_positions):
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


def determine_mosaic_dimensions(image : BioImage):
    """Determine the mosaic dimensions and positions from the image metadata.
    
    Parameters
    ----------
    image : BioImage
        The BioImage object.
    
    Returns
    -------
    mosaic_dim : str
        The mosaic dimension ("M" or "scene").
    """
    if getattr(image.dims,"M",0) > 1:
        mosaic_dim = "M"
    elif len(image.scenes) > 1:
        mosaic_dim = "I" # For scene dimension
        #raise NotImplementedError("Mosaic positions for 'scene' dimension are not implemented.")
    else:
        mosaic_dim = None
    return mosaic_dim

@dataclass
class Config:
    file_path : str = "testdata/test.czi"
    output_path : str = "testdata/test_output"
    output_metadata_filename : str = "metadata.yaml"
    output_test_image_filename_prefix : str = "stitched"
    

def main():
    cfg = pyrallis.parse(config_class=Config)
    print(f"File Path: {cfg.file_path}")
    print(f"Output path: {cfg.output_path}")
    output_metadata_path = path.join(cfg.output_path, cfg.output_metadata_filename)

    image = BioImage(cfg.file_path, 
                     reconstruct_mosaic=False, 
                     use_aicspylibczi=True)

    mosaic_dim = determine_mosaic_dimensions(image)
    acquired_times : list[dict] = frame_acquisition_times(image) # This is a global list
    acquired_times = [
        {str(k): int(v) if k!="acquired_time" else str(v.astype(str)) for k,v in t.items()}
        for t in acquired_times
    ]
    if mosaic_dim == "M":
        scenes = image.scenes
        acquired_times_by_scene = {s: [] for s in scenes}
        for t in acquired_times:
            scene_index = t.get("I",0)
            acquired_times_by_scene[scenes[scene_index]].append(t)
    else:
        scenes = [None]
        acquired_times_by_scene = {None: acquired_times}
    
    # Export metadata to YAML
    def cast_pixel_size(value):
        try:
            return float(value)
        except:
            return None
    
    all_metadata = {}
    for scene in scenes:
        if scene is not None:
            image.set_scene(scene)
        if mosaic_dim == "M":
            mosaic_positions = np.array(image.get_mosaic_tile_positions())
        elif mosaic_dim == "I":
            raise NotImplementedError("Mosaic positions for 'scene' dimension are not implemented.")
        
        print(f"Scene: {scene}")
        print(f"  Dimensions: {image.dims}")
        print(f"  Physical Pixel Sizes (microns): Z={image.physical_pixel_sizes.Z}, Y={image.physical_pixel_sizes.Y}, X={image.physical_pixel_sizes.X}")
        
        metadata=dict(
            file_path=path.abspath(cfg.file_path),
            metadata_path = path.abspath(output_metadata_path),
            channel_names = list(map(str,image.channel_names)), # channel name strings
            dims = dict(image.dims.items()), # dimensions of the image
            mosaic_dim = mosaic_dim,
            mosaic_positions_px = mosaic_positions.tolist() if mosaic_positions is not None else None,
            physical_pixel_sizes_um = {
                "Z": cast_pixel_size(image.physical_pixel_sizes.Z),
                "Y": cast_pixel_size(image.physical_pixel_sizes.Y),
                "X": cast_pixel_size(image.physical_pixel_sizes.X)
            }, # physical pixel sizes in microns
            acquired_times = acquired_times_by_scene[scene]
        )
        all_metadata[scene] = metadata
       
        if mosaic_dim == "I": 
            xr_image = image.get_xarray_dask_stack()
        else:
            xr_image = image.xarray_dask_data
        dim_squeeze = [d for d in xr_image.dims if d not in [mosaic_dim,"Y","X"]]
        xr_image_sel = xr_image.isel({d:0 for d in dim_squeeze}) 
        np_image = xr_image_sel.transpose(mosaic_dim,"Y","X").to_numpy()
        mosaic = merge_mosaic_images(np_image, mosaic_positions)

        plt.figure(figsize=(10,10))
        plt.imshow(mosaic)
        output_test_image_path = path.join(
            cfg.output_path, 
            f"{cfg.output_test_image_filename_prefix}" + (f"_{scene}" if scene is not None else "") + ".png"
        )
        print(f"  Saving test stitched image to: {output_test_image_path}")
        plt.savefig(output_test_image_path, bbox_inches='tight')
        plt.close()

    if all_metadata.keys() == [None]:
        all_metadata["all_scenes"] = all_metadata.pop(None)

    os.makedirs(path.dirname(output_metadata_path),exist_ok=True)
    with open(output_metadata_path, "w") as f:
        yaml.dump(all_metadata, f)

    if mosaic_positions is None:
        print("Mosaic positions are not available. Exiting.")
        return
    
if __name__ == '__main__':
    main()