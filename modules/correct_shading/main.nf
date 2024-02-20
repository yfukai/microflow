process ESTIMATE_SHADING_EACH {
    conda "${projectDir}/env/conda_env.yaml"
    errorStrategy 'retry'
    maxForks 4
    maxRetries 3
    cache true
    cpus 10

    publishDir "${params.output_path}/${output_dir}/notebooks", pattern: '*.ipynb', mode: "copy"
    publishDir "${params.output_path}/${output_dir}", pattern: 'shading_profile.zarr', mode: "symlink"
    
    input:
    tuple val(output_dir), path("original_image.nd2"), path("metadata.yaml")

    output:
    tuple val(output_dir), path("shading_profile.zarr")
    path("*.ipynb")

    """
    PYTHONPATH="${projectDir}/scripts:${projectDir}/scripts/b1_shading_correction_median" \
        papermill ${projectDir}/scripts/b1_shading_correction_median/each_frame/b1_a_shading_estimation.ipynb \
        b1_a_shading_estimation.ipynb \
        -p file_path "original_image.nd2" \
        -p output_dir "./" \
        -p metadata_path "metadata.yaml" \
        -p profile_filename "shading_profile.zarr" \
        -p strategy "${params.shading_estimation_strategy}" \
        -p robust ${params.shading_correction_median_robust} \
        -p num_cpus 10
    """
}

process CORRECT_SHADING_EACH {
//    errorStrategy 'retry'
//    maxForks 2 
//    maxRetries 3
    cache true
    cpus 10

    publishDir "${params.output_path}/${output_dir}/notebooks", pattern: '*.ipynb', mode: "copy"
    publishDir "${params.output_path}/${output_dir}", pattern: 'shading_corrected.zarr', mode: "symlink"

    input:
    tuple val(output_dir), path("original_image.nd2"), path("metadata.yaml"), path("shading_profile.zarr")

    output:
    tuple val(output_dir), path("shading_corrected.zarr")
    path("*.ipynb")

    """
    PYTHONPATH="${projectDir}/scripts:${projectDir}/scripts/b1_shading_correction_median" \
        papermill ${projectDir}/scripts/b1_shading_correction_median/each_frame/b1_a_shading_estimation.ipynb \
        -p file_path "original_image.nd2" \
        -p output_dir "./" \
        -p metadata_path "metadata.yaml" \
        -p profile_filename "shading_profile.zarr" \
        -p corrected_filename "shading_corrected.zarr" \
        -p strategy "${params.shading_estimation_strategy}" \
        -p robust ${params.shading_correction_median_robust} \
        -p mode = "additive"
        -p num_cpus 10


strategy = "timewise" # or "all"
local_subtraction_channels = "*DIA*"
local_subtraction_scaling = 0.1
local_subtraction_median_disk_size=4
num_cpus=10
    """
}