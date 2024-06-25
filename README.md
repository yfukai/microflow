# Microflow: a prototype Nextflow workflow for microscopy image preprocessing 

## About

This is a prototyping attempt of a common image processing workflow using [Nextflow](https://nextflow.io/). 
The steps include:
- Organizing and exporting image metadata into a YAML file.
- Estimating shading profiles and correcting the shading effect.
- Stitching (by [M2Stitch](https://github.com/yfukai/m2stitch)) into a Zarr array.

All the steps are written as a Jupyter notebook and run by [Papermill](https://github.com/nteract/papermill) in the workflow.

## How to use

1. Create a list of files to process (currently [`AICSImageIO`](https://github.com/AllenCellModeling/aicsimageio) compatible files work). 

2. Execute the workflow. The parameters are as follows:
    - `-w` : The working directory for Nextflow.
    - `--input_path_csv` : The CSV file for the file list.
    - `--common_input_path` : The "root" directory of the image files. The output images are stored preserving the subdirectory structure with respect to this directory. 
    - `--output_path` : The directory in which output images are stored.
    ```bash
    nextflow run path/to/microflow \
        -resume \
        -w /path/to/workdir/ \
        --input_path_csv "./file_list.txt" \
        --common_input_path "/mnt/showers/Cell-picker/240119/" \
        --output_path "/path/to/output/"
    ```
    One can also specify the following parameters:
    - `--shading_estimation_strategy` = "timewise" // or "all" : If "timewise", estimate the shading profile for each  frame. If "all", use the all frames.
    - `--shading_estimation_median_robust` = "False" // or "True" : If True, use the intensities within the 2*(Median absolute deviation from median) around the median.
    - `--shading_estimation_median_filter_size` = 3 : Median filter size for shading correction.
    - `--shading_estimation_gaussian_filter_size` = 40  : Gaussian filter size for shading correction.
    - `--shading_correction_mode` = "additive" // or "multiplicative" : The shading correction mode.
    - `--shading_correction_local_subtraction_channels` = "*DIA*" : The channel pattern for shading correction by local intensity subtraction.
    - `--shading_correction_local_subtraction_scaling` = 0.1
    - `--shading_correction_local_subtraction_median_disk_size` = 4
    - `--stitching_stitch_every_t` = 0 : The frame skip for stitching. If zero, only use the first frame for stitching.
    - `--stitching_target_channel` = '10x_Fukai_DIA_IS' : The reference channel for stitching.


# Todo 
[] Adding other shading correction / stitching methods
[] Reorganizing input / output image formats
[] Organizing documentation
[] Splitting each step to command line tools 
[] Deploying to nf-core