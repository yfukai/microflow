#!/usr/bin/env python3 

import pyrallis
from dataclasses import dataclass
from functools import partial

from os import path
import yaml
import numpy as np
from matplotlib import pyplot as plt
from m2stitch import stitch_images
import multiprocessing as mp
import pandas as pd
import joblib

from utils import (
    parse_positions_to_pairs,
    merge_mosaic_images,
)
from tensorstore_utils import init_store

@dataclass
class Config:
    file_path : str = "testdata/shading_corrected.zarr"
    metadata_path : str = "testdata/metadata.yaml"
    scene : str = '1.1%-50ms' #TODO change to int since the scene names may overlap
    stitch_every_t : int = 10
    try_ncc_thresholds = [0.1, 0.2, 0.3]

    output_path : str = "testdata/test_output"
    output_run_config_filename : str = "run_config.yaml"
    output_position_name : str = "mosaic_positions.csv"
    output_test_image_name : str = "test_stitched_image.png"
    
    num_cpus : int = mp.cpu_count()

def stitch_T(T, *, file_path, try_ncc_thresholds, index_positions, mosaic_positions):
    image = init_store(file_path, mode="r") #In TMZYX order
    target_images = image[T, :, 0].read().result()  # Target channel only
    positions = None
    for ncc_threshold in try_ncc_thresholds:
        try: 
            positions, _ = stitch_images(
                target_images,
                position_indices = index_positions,
                position_initial_guess = mosaic_positions,
                row_col_transpose=False,
                ncc_threshold=ncc_threshold,
            )
            break
        except AssertionError as e:
            if "try lowering the ncc_threshold" in str(e):
                continue
            else:
                raise e
    if positions is None:
        raise ValueError("Stitching failed.")
    return positions.assign(T=T)
    
def main():
    cfg = pyrallis.parse(Config)
    output_run_config_path = path.join(cfg.output_path, cfg.output_run_config_filename)
    with open(output_run_config_path, "w") as f:
        pyrallis.dump(cfg, f)
    
    image = init_store(cfg.file_path, mode="r") #In TMZYX order
    with open(cfg.metadata_path, "r") as f:
        metadata = yaml.safe_load(f)

    print(f"Image shape: {image.shape}")
    metadata = metadata[cfg.scene]
    if image.shape[2] > 1:
        raise ValueError("Currently only single Z slice images are supported.")
    mosaic_positions = np.array(metadata['mosaic_positions_px'])
    print(f"Mosaic positions shape: {mosaic_positions.shape}")
    assert len(mosaic_positions) == image.shape[1]

    #################### Calculate position indices ####################
    pairs =  parse_positions_to_pairs(
        image.shape[-2:],
        estimated_positions = mosaic_positions,
        overlap_threshold_percentage  = 2,
    )

    position_indices : list = [None for _ in range(len(mosaic_positions))]
    position_indices[0] = np.array([0,0], dtype=int)

    # Change absolute positions to index difference (removed after migrating to microtailor)
    for i in range(10):
        for i, row in pairs.iterrows():
            for sign, (i1, i2) in zip([1,-1],[(row.image_index1,row.image_index2),(row.image_index2,row.image_index1)]):
                if position_indices[i1] is not None:
                    disp = row.estimated_displacement
                    index_displacement = (np.abs(disp) > np.min(image.shape[-2:])*0.5).astype(int) * np.sign(disp) * sign
                    calc_pos = position_indices[i1] + index_displacement

                    if position_indices[i2] is None:
                        position_indices[i2] = calc_pos
                    else:
                        assert np.all(position_indices[i2] == calc_pos)
    assert not np.any([p is None for p in position_indices])
    position_indices = np.array(position_indices)
    position_indices -= np.min(position_indices,axis=0)
    position_indices = position_indices.astype(int)

    print(position_indices[:10])

    # %%
    target_Ts = [0] if cfg.stitch_every_t == 0 else list(range(0, image.shape[0], cfg.stitch_every_t))
    print(f"Target Ts: {target_Ts}")

    ####################### Visualize one target T #######################
    qs = np.percentile(
        np.concatenate([
            np.ravel(image[target_T,0,0].read().result()) 
            for target_T in target_Ts]),q=[1,99])
    plt.imshow(image[target_Ts[0],0,0].read().result(),vmax=qs[1],vmin=qs[0])
    plt.colorbar()

    ###################### Perform stitching ######################
    def stitch_T_fn(T):
        try:
            return stitch_T(
                T, 
                file_path=cfg.file_path, 
                try_ncc_thresholds=cfg.try_ncc_thresholds,
                index_positions=position_indices, 
                mosaic_positions=mosaic_positions
            )
        except Exception as e:
            print(f"Stitching failed for T={T}: {e}")
            return pd.DataFrame()

    T = target_Ts[0]
    positions = list(joblib.Parallel(n_jobs=cfg.num_cpus)(
        joblib.delayed(stitch_T_fn)(_T) for _T in [T]
    ))[0]
    if positions.empty:
        raise ValueError(f"Stitching failed for T={T}, cannot save test image.")

    stitched = merge_mosaic_images(image[T,:,0].read().result(), positions[["y_pos","x_pos"]].values)
    plt.figure(figsize=(10,10))
    plt.imshow(stitched[:,:],vmin=qs[0],vmax=qs[1])
    plt.colorbar()
    output_test_image_path = path.join(cfg.output_path, cfg.output_test_image_name)
    plt.savefig(output_test_image_path, dpi=300, bbox_inches='tight')
    print(f"Saved test stitched image to {output_test_image_path}")

    all_positions = [positions]
    if len(target_Ts) > 1:
        all_positions.extend(joblib.Parallel(n_jobs=cfg.num_cpus)(
            joblib.delayed(stitch_T_fn)(_T) for _T in target_Ts[1:] 
        ))
    all_positions_df=pd.concat(all_positions)
    output_position_path = path.join(cfg.output_path, cfg.output_position_name)
    all_positions_df.to_csv(output_position_path, index=False)
    print(f"Saved all positions to {output_position_path}")

if __name__ == "__main__":
    main()