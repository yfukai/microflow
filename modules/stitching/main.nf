process STITCHING {
    conda "${projectDir}/env/conda_env.yaml"
    errorStrategy 'ignore'
//    maxRetries 3
    maxForks 4 
    cpus 8 
    cache true

    publishDir "${params.output_path}/${output_dir}", \
        pattern: "{stitching_result.csv}", \
        mode: "copy"
    publishDir "${params.output_path}/${output_dir}/notebooks", \
        pattern: "{*.ipynb}", \
        mode: "copy"
    publishDir "${params.output_path}/${output_dir}", \
        pattern: "stitched.zarr", \
        mode: "symlink"

    input :
    tuple val(output_dir), path("metadata.yaml"), path("shading_corrected.zarr")

    output :
    tuple path("stitched.zarr"), val(output_dir)
    path "stitching_result.csv" 
    path "c_stitching.ipynb"

    """
    PYTHONPATH="${projectDir}/scripts" papermill ${projectDir}/scripts/c_stitching.ipynb \
        c_stitching.ipynb  \
        -p file_path shading_corrected.zarr \
        -p output_dir ./ \
        -p metadata_path "metadata.yaml" \
        -p output_image_name "stitched.zarr" \
        -p output_csv_name "stitching_result.csv" \
        -p stitch_every_t ${params.stitching_stitch_every_t} \
        -p num_cpus ${task.cpus} \
        -p target_channel '${params.stitching_target_channel}'
    """
}