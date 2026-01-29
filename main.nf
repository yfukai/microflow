nextflow.enable.dsl=2
nextflow.enable.moduleBinaries = true

params.input_path_csv = null
params.common_input_path = null
params.output_path = null
params.shading_correction = "none"
params.shading_correction_mode = "additive"
params.local_subtraction_channels = "all"

include { EXPORT_ORIGINAL_FILENAME } from "./modules/misc"
include { EXPORT_METADATA } from "./modules/export_metadata"
//include { ESTIMATE_SHADING_EACH; CORRECT_SHADING_EACH } from "./modules/correct_shading"
//include { STITCHING } from "./modules/stitching"

workflow {
    image_files = Channel.fromPath(params.input_path_csv) | splitCsv() \
        | filter { !(it[0] =~ /^#/) } | map({ 
            relpath=params.common_input_path.toURI()
                          .relativize(it[0].toURI())
                          .toString()
            [[output_dir:relpath+"_analyzed"], it[0]] 
       })
    EXPORT_ORIGINAL_FILENAME(image_files)
    EXPORT_METADATA(image_files)

    metadata = EXPORT_METADATA.out[0]
    // Populate scenes_channels into metadata, and make a (meta, scene, channel_index list)
    image_files.join(metadata).set { image_files_metadata }
    image_files_metadata.map { meta, image_file, metadata_yaml, scenes_channels_yaml ->
        def scenes_channels = new groovy.yaml.YamlSlurper().parseText(metadata_yaml.text)
        val = []
        for (scene_channel in scenes_channels) {
            meta2 = meta + scene_channel
            val << [meta2, image_file, metadata_yaml]
        }
    }.flatMap().set { image_files_metadata_expanded }
    image_files_metadata_expanded.view()

//    CORRECT_SHADING_EACH_FRAME(image_files_metadata)
//
//    shading_corrected = CORRECT_SHADING_EACH.out[0].collect()
//    metadata.join(shading_corrected).set { image_files_metadata_shading_corrected }
//    //image_files_metadata_shading_corrected.view()
//    STITCHING(image_files_metadata_shading_corrected)

}

