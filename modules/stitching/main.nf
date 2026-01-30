process STITCHING_ESTIMATION {
    conda "${moduleDir}/env/conda.yaml"
    tag "stitching_estimation_${meta.output_dir}_${meta.scene}_${meta.channel_index}_${meta.channel_name}"
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

process SUMMARIZE_STITCHING_POSITIONS_PER_FILE {
    conda "${moduleDir}/env/conda.yaml"
    cache true

    publishDir "${params.output_path}/${meta.output_dir}", \
        pattern: "stitching_result_summary_${meta.scene}.csv", \
        mode: "copy"

    input :
    tuple val(meta), path("positions.csv")

    output :
    tuple val(meta), path("stitching_result_summary_${meta.scene}.csv")

    """
    summarize_mosaic_positions.py  \
            --file_path positions.csv \
            --output_path ./ \
            --output_filename "stitching_result_summary_${meta.scene}.csv" \
    """
}


process STITCHING_EXPORT {
    conda "${moduleDir}/env/conda.yaml"
    errorStrategy 'ignore'
    maxForks 4 
    cpus 8 
    cache true

    publishDir "${params.output_path}/${meta.output_dir}", \
        pattern: "${meta.output_image_name}", \
        mode: "copy"
    publishDir "${params.output_path}/${meta.output_dir}/qc/stitching", \
        pattern: "test_stitched_export_image.png", \
        mode: "copy"
    publishDir "${params.output_path}/${meta.output_dir}/qc/stitching", \
        pattern: "run_config_export*.yaml", \
        mode: "copy"

    input :
    tuple val(meta), path(shading_corrected_zarr), path(stitching_positions_csv)

    output :
    tuple val(meta), path("stitched.zarr")
    path("test_stitched_export_image.png")
    path("run_config_export_${meta.scene}_${meta.channel_index}_${meta.channel_name}.yaml")

    """
    stitching_export.py  \
        --file_path ${shading_corrected_zarr} \
        --positions_df_path ${stitching_positions_csv} \
        --output_path ./ \
        --output_run_config_filename "run_config_export_${meta.scene}_${meta.channel_index}_${meta.channel_name}.yaml" \
        --output_image_name "stitched.zarr" \
        --output_test_image_name "test_stitched_export_image_${meta.scene}_${meta.channel_index}_${meta.channel_name}.png"
    """
}