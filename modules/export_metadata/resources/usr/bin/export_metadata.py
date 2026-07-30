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
from get_stage_positions import scene_mosaic_positions_px

# Name of the pseudo scene used when the file is treated as a single scene,
# either because it has no scene dimension or because the scenes are the mosaic tiles.
ALL_SCENES = "all_scenes"


def open_image(file_path : str) -> BioImage:
    """Open an image file, keeping the mosaic tiles separate.

    Parameters
    ----------
    file_path : str
        Path to the image file.

    Returns
    -------
    BioImage
        The BioImage object.
    """
    # `use_aicspylibczi` is understood only by the CZI reader, and the other readers
    # reject unknown keyword arguments.
    reader_kwargs = {"use_aicspylibczi": True} if file_path.lower().endswith(".czi") else {}
    return BioImage(file_path, reconstruct_mosaic=False, **reader_kwargs)


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


def to_unique_channel_names(channel_names : list[str]) -> list[str]:
    """Convert channel names to unique channel names by appending indices to duplicates.

    The first occurrence of a name is kept as is and the following ones are numbered
    from 2, so that e.g. two "Bright" channels become "Bright" and "Bright_2". This is
    the convention the CZI channel names already follow.

    Parameters
    ----------
    channel_names : list of str
        List of channel names.

    Returns
    -------
    list of str
        List of unique channel names.
    """
    name_count = {}
    unique_names = []
    for name in channel_names:
        name_count[name] = name_count.get(name, 0) + 1
        count = name_count[name]
        unique_names.append(name if count == 1 else f"{name}_{count}")
    return [str(n) for n in unique_names]


@dataclass
class Config:
    file_path : str = "testdata/test.czi"
    output_path : str = "testdata/test_output"
    output_run_config_filename : str = "run_config.yaml"
    output_metadata_filename : str = "metadata.yaml"
    output_test_image_filename_prefix : str = "stitched"
    

def main():
    cfg = pyrallis.parse(config_class=Config)
    print(f"File Path: {cfg.file_path}")
    print(f"Output path: {cfg.output_path}")
    output_metadata_path = path.join(cfg.output_path, cfg.output_metadata_filename)
    output_run_config_path = path.join(cfg.output_path, cfg.output_run_config_filename)
    with open(output_run_config_path, "w") as f:
        pyrallis.dump(cfg, f)

    image = open_image(cfg.file_path)

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
        # The scenes are the mosaic tiles (or there is only one scene), so the whole
        # file is exported as a single pseudo scene.
        scenes = [ALL_SCENES]
        acquired_times_by_scene = {ALL_SCENES: acquired_times}
    
    # Export metadata to YAML
    def cast_pixel_size(value):
        try:
            return float(value)
        except:
            return None
    
    all_metadata = {}
    for scene in scenes:
        if scene != ALL_SCENES:
            image.set_scene(scene)
        if mosaic_dim == "M":
            mosaic_positions = np.array(image.get_mosaic_tile_positions())
        elif mosaic_dim == "I":
            mosaic_positions = scene_mosaic_positions_px(image)
        else:
            mosaic_positions = None

        print(f"Scene: {scene}")
        print(f"  Dimensions: {image.dims}")
        print(f"  Physical Pixel Sizes (microns): Z={image.physical_pixel_sizes.Z}, Y={image.physical_pixel_sizes.Y}, X={image.physical_pixel_sizes.X}")
        
        metadata=dict(
            file_path=path.abspath(cfg.file_path),
            metadata_path = path.abspath(output_metadata_path),
            channel_names = list(map(str,image.channel_names)), # channel name strings
            unique_channel_names = to_unique_channel_names(image.channel_names), # unique channel name strings
            dims = dict(image.dims.items()), # dimensions of the image
            mosaic_dimension = mosaic_dim,
            mosaic_positions_px = mosaic_positions.tolist() if mosaic_positions is not None else None,
            physical_pixel_sizes_um = {
                "Z": cast_pixel_size(image.physical_pixel_sizes.Z),
                "Y": cast_pixel_size(image.physical_pixel_sizes.Y),
                "X": cast_pixel_size(image.physical_pixel_sizes.X)
            }, # physical pixel sizes in microns
            acquired_times = acquired_times_by_scene[scene]
        )
        all_metadata[scene] = metadata

        if mosaic_dim is None:
            print("  Not a mosaic image, skipping the test stitched image.")
            continue
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
            f"{cfg.output_test_image_filename_prefix}_{scene}.png"
        )
        print(f"  Saving test stitched image to: {output_test_image_path}")
        plt.savefig(output_test_image_path, bbox_inches='tight')
        plt.close()

    os.makedirs(path.dirname(output_metadata_path),exist_ok=True)
    with open(output_metadata_path, "w") as f:
        yaml.dump(all_metadata, f)

    if mosaic_positions is None:
        print("Mosaic positions are not available. Exiting.")
        return
    
if __name__ == '__main__':
    main()