nextflow.enable.dsl=2

params.input_path_csv = null
params.common_input_path = ""
params.output_path = ""
params.shading_correction = "none"
params.shading_correction_mode = "additive"
params.local_subtraction_channels = "all"

include { exportOriginalFilename } from "./modules/misc"
include { exportMetadata } from "./modules/export_metadata"

workflow {
    image_files = Channel.fromPath(params.input_path_csv) | splitCsv() \
        | filter { !(it[0] =~ /^#/) } | map({ 
            relpath=params.common_input_path.toURI()
                          .relativize(it[0].toURI())
                          .toString()
            [it[0],relpath+"_analyzed"] 
       })
    exportOriginalFilename(image_files)
    exportMetadata(image_files)
}

process correctShading {
    errorStrategy 'retry'
    maxForks 2 
    maxRetries 3
    cache true
    cpus 10

    publishDir "${params.output_path}/${output_dir}", pattern: 'c_shading_correction.ipynb', mode: "copy"
    publishDir "${params.output_path}/${output_dir}", pattern: 'shading_corrected.zarr', mode: "symlink"
    
    input:
    tuple path(image_file_path), path("metadata.yaml"), val(output_dir)

    output:
    tuple path("shading_corrected.zarr"), path("metadata.yaml"), val(output_dir)
    path("c_shading_correction.ipynb")

    """
    PYTHONPATH="${projectDir}/scripts" papermill ${projectDir}/scripts/c_shading_correction.ipynb \
        c_shading_correction.ipynb  \
        -p file_path ${image_file_path} \
        -p metadata_path "metadata.yaml" \
        -p output_image_path "shading_corrected.zarr" \
        -p shading_result_path None \
        -p num_cpus 10 \
        -p mode ${params.shading_correction_mode} \
        -p local_subtraction_channels ${params.local_subtraction_channels} 
    """
}

process stitching {
    errorStrategy 'retry'
    maxRetries 3
    maxForks 4 
    cpus 8 
    cache true

    publishDir "${params.output_path}/${output_dir}", \
        pattern: "{metadata.yaml,stitching_result.csv,d_stitching.ipynb}", \
        mode: "copy"
    publishDir "${params.output_path}/${output_dir}", \
        pattern: "stitched.zarr", \
        mode: "symlink"

    input :
    tuple path("shading_corrected.zarr"), path("metadata.yaml"), val(output_dir)

    output :
    tuple path("stitched.zarr"), path("metadata.yaml"), val(output_dir)
    path "stitching_result.csv" 
    path "d_stitching.ipynb"

    """
    PYTHONPATH="${projectDir}/scripts" papermill ${projectDir}/scripts/d_stitching.ipynb \
        d_stitching.ipynb  \
        -p file_path shading_corrected.zarr \
        -p metadata_path "metadata.yaml" \
        -p output_image_path "stitched.zarr" \
        -p output_csv_path "stitching_result.csv" \
        -p every_t_stitch 0 \
        -p num_cpus 8 \
        -p target_channel '10x_Fukai_DIA_IS'
    """
}


//process report {
//    publishDir "${params.output_path}/${output_dir}", pattern: "report", mode: "copy"
//
//    input :
//    tuple file("stitched.zarr"), file("metadata.yaml"), val(output_dir) from stitchedMetadata
//
//    output : 
//    val(output_dir) into reported
//    file "report" 
//
//    """
//    ${moduleDir}/scripts/d_report.py \
//        stitched.zarr \
//        metadata.yaml \
//        report
//    """
//}
//
