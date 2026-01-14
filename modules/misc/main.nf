params.output_path = null

process EXPORT_ORIGINAL_FILENAME {
    publishDir "${params.output_path}/${output_dir}", pattern: 'original_filenames.txt', mode: "copy"

    input : 
        tuple val(output_dir), val(image_file_path)
    output :
        path("original_filenames.txt")

    """
    echo '${image_file_path}' > original_filenames.txt
    """

}