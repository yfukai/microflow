process EXPORT_METADATA {
    conda "${projectDir}/env/conda_env.yaml"

    //errorStrategy 'retry'
    //maxRetries 3
    maxForks 20
    cache true

    publishDir "${params.output_path}/${output_dir}", pattern: '{metadata.yaml}', mode: "copy"
    publishDir "${params.output_path}/${output_dir}/notebooks", pattern: '{a_export_metadata.ipynb}', mode: "copy"

    input : 
    tuple val(output_dir), path(image_file_path)

    output :
    tuple val(output_dir), path("metadata.yaml")
    file("a_export_metadata.ipynb")

    """
    PYTHONPATH="${projectDir}/scripts" papermill ${projectDir}/scripts/a_export_metadata.ipynb \
        a_export_metadata.ipynb \
        -p file_path ${image_file_path} \
        -p output_metadata_path metadata.yaml
    """
}
