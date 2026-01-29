process CORRECT_SHADING_EACH_FRAME {
    conda "${projectDir}/env/conda_env.yaml"
//    errorStrategy 'retry'
//    maxForks 2
//    maxRetries 3
    cache true
//    cpus 4

    publishDir "${params.output_path}/${output_dir}/notebooks", pattern: '*.ipynb', mode: "copy"
    publishDir "${params.output_path}/${output_dir}", pattern: 'shading_profile.zarr', mode: "symlink"
    
    input:
    tuple val(output_dir), path(image_file_path), path("metadata.yaml")

    output:
    tuple val(output_dir), path("shading_corrected.zarr")
    path("*.ipynb")

    """

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