process CORRECT_SHADING_EACH_FRAME {
    conda "${moduleDir}/env/conda.yaml"
    errorStrategy 'ignore'
    maxForks 10
//    maxRetries 3
    cache true
    cpus 4

    publishDir({ "${params.output_path}/${meta.output_dir}/qc/correct_shading" }), pattern: "shading_correction_result*.png", mode: "copy"
    publishDir({ "${params.output_path}/${meta.output_dir}/qc/correct_shading" }), pattern: "run_config*.yaml", mode: "copy"
    //publishDir "${params.output_path}/${meta.output_dir}/qc/correct_shading", pattern: 'shading_profile.zarr', mode: "symlink"

    input:
    tuple val(meta), path(image_file_path), path("metadata.yaml")

    output:
    tuple val(meta), path("shading_corrected.zarr")
    path("shading_correction_result*.png")
    path("run_config*.yaml")

    """
    correct_shading.py \
        --file_path "${image_file_path}" \
        --metadata_path "metadata.yaml" \
        --scene "${meta.scene}" \
        --channel_index ${meta.channel_index} \
        --output_path "./" \
        --output_run_config_filename "run_config_${meta.scene}_${meta.channel_index}_${meta.channel_name}.yaml" \
        --output_correction_data_filename "shading_correction_${meta.scene}_${meta.channel_index}_${meta.channel_name}.zarr" \
        --output_test_image_filename "shading_correction_result_${meta.scene}_${meta.channel_index}_${meta.channel_name}.png" \
        --output_image_name "shading_corrected.zarr" \
        --num_cpus ${task.cpus} 
    """
}
