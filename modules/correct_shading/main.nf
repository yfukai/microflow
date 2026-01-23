process EXPORT_METADATA {
    conda "${moduleDir}/env/conda.yaml"

    cache true

    publishDir "${params.output_path}/${output_dir}", pattern: '{metadata.yaml}', mode: "copy"
    publishDir "${params.output_path}/${output_dir}/qc/export_metadata/", pattern: '{stitched.png}', mode: "copy"

    input : 
    tuple val(output_dir), path(image_file_path)

    output :
    tuple val(output_dir), path("metadata.yaml")
    path("stitched.png")

    """
    export_metadata.py \
        --file_path ${image_file_path} \
        --output_metadata_path metadata.yaml
        --output_test_image_path stitched.png
    """
}
process ESTIMATE_SHADING_EACH {
    conda "${projectDir}/env/conda_env.yaml"
    errorStrategy 'retry'
    maxForks 2
    maxRetries 3
    cache true
    cpus 4

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
        -p strategy ${params.shading_estimation_strategy} \
        -p robust ${params.shading_estimation_median_robust} \
        -p median_filter_size ${params.shading_estimation_median_filter_size} \
        -p gaussian_filter_size ${params.shading_estimation_gaussian_filter_size} \
        -p num_cpus ${task.cpus}
    """
}

process CORRECT_SHADING_EACH {
    conda "${projectDir}/env/conda_env.yaml"
    //errorStrategy 'ignore'
    maxForks 2
    cache true
    cpus 4

    publishDir "${params.output_path}/${output_dir}/notebooks", pattern: '*.ipynb', mode: "copy"
    publishDir "${params.output_path}/${output_dir}", pattern: 'shading_corrected.zarr', mode: "symlink"

    input:
    tuple val(output_dir), path("original_image.nd2"), path("metadata.yaml"), path("shading_profile.zarr")

    output:
    tuple val(output_dir), path("shading_corrected.zarr")
    path("*.ipynb")

    """
    PYTHONPATH="${projectDir}/scripts:${projectDir}/scripts/b1_shading_correction_median" \
        papermill ${projectDir}/scripts/b1_shading_correction_median/each_frame/b1_b_shading_correction.ipynb \
        b1_b_shading_correction.ipynb \
        -p file_path "original_image.nd2" \
        -p output_dir "./" \
        -p metadata_path "metadata.yaml" \
        -p profile_filename "shading_profile.zarr" \
        -p corrected_filename "shading_corrected.zarr" \
        -p mode ${params.shading_correction_mode} \
        -p local_subtraction_channels "${params.shading_correction_local_subtraction_channels}" \
        -p local_subtraction_scaling ${params.shading_correction_local_subtraction_scaling} \
        -p local_subtraction_median_disk_size ${params.shading_correction_local_subtraction_median_disk_size} \
        -p num_cpus ${task.cpus} 
    """
}
