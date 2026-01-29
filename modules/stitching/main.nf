process STITCHING_ESTIMATION {
    conda "${moduleDir}/env/conda.yaml"
    errorStrategy 'ignore'
    maxForks 4 
    cpus 8 
    cache true

    publishDir "${params.output_path}/${meta.output_dir}", \
        pattern: "stitching_result_${meta.scene}.csv", \
        mode: "copy"
    publishDir "${params.output_path}/${meta.output_dir}/qc/stitching", \
        pattern: "test_stitched_image_${meta.scene}.png", \
        mode: "copy"
    publishDir "${params.output_path}/${meta.output_dir}/qc/stitching", \
        pattern: "run_config*.png", \
        mode: "copy"

    input :
    tuple val(meta), path(shading_corrected_zarr), path(metadata_yaml)

    output :
    tuple val(meta), path("stitching_result_${meta.scene}.csv")
    path("test_stitched_image_${meta.scene}.png")
    path("run_config_${meta.scene}_${meta.channel_index}_${meta.channel_name}.yaml")


    """
    stitching_estimation.py  \
        --file_path ${shading_corrected_zarr} \
        --metadata_path ${metadata_yaml} \
        --scene ${meta.scene} \
        --stitch_every_t ${params.stitching_stitch_every_t} \
        --output_path ./ \
        --output_run_config_filename "run_config_${meta.scene}_${meta.channel_index}_${meta.channel_name}.yaml" \
        --output_position_name "stitching_result_${meta.scene}.csv" \
        --output_test_image_name "test_stitched_image_${meta.scene}.png"
    """
}