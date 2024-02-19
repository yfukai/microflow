params.output_path = null

process exportOriginalFilename {
    publishDir "${params.output_path}/${output_dir}", pattern: 'original_filename.txt', mode: "copy"

    input : 
        tuple val(image_file_path), val(output_dir)
    output :
        path("original_filename.txt")

    """
    echo '${image_file_path}' > original_filename.txt
    """

}