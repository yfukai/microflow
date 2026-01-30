nextflow.enable.dsl=2
nextflow.enable.moduleBinaries = true

params.input_path_csv = null
params.common_input_path = null
params.output_path = null
params.shading_correction_config_path = null
params.stitching_target_channel = "Bright"
params.stitching_stitch_every_t = 1

include { EXPORT_ORIGINAL_FILENAME } from "./modules/misc"
include { EXPORT_METADATA } from "./modules/export_metadata"
include { CORRECT_SHADING_EACH_FRAME } from "./modules/correct_shading"
include { STITCHING_ESTIMATION; SUMMARIZE_STITCHING_POSITIONS_PER_FILE; STITCHING_EXPORT } from "./modules/stitching"


workflow {
    if (!params.input_path_csv) {
        error "Please provide --input_path_csv"
    }
    if (!params.common_input_path) {
        error "Please provide --common_input_path"
    }
    if (!params.output_path) {
        error "Please provide --output_path"
    }
    def shading_correction_config = [:]
    if (params.shading_correction_config_path) {
        def config = new groovy.yaml.YamlSlurper().parse(
            new File(params.shading_correction_config_path)
        )
        for (entry in config) {
            // show type of entry.value
            def value = entry.value
            builder = new groovy.yaml.YamlBuilder()
            builder.call(value as Map)
            shading_correction_config[entry.key] = builder.toString()
        }
    }

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
        def scenes_channels = new groovy.yaml.YamlSlurper().parseText(scenes_channels_yaml.text)
        def val = []
        for (scene_channel in scenes_channels) {
            if (scene_channel.channel_name in shading_correction_config) {
                shading_correction_config_str = shading_correction_config[scene_channel.channel_name]
            } else {
                shading_correction_config_str = null
            }
            def meta2 = meta + scene_channel
            val << [meta2, image_file, metadata_yaml, shading_correction_config_str]
        }
        val
    }.flatMap().set { image_files_metadata_expanded }

    CORRECT_SHADING_EACH_FRAME(image_files_metadata_expanded)

    shading_corrected = CORRECT_SHADING_EACH_FRAME.out[0]
    shading_corrected.filter { meta, shading_corrected_zarr, metadata_yaml ->
        meta.channel_name.equals(params.stitching_target_channel)
    }.set { shading_corrected_target_channel }
    STITCHING_ESTIMATION(shading_corrected_target_channel)
    stitching_estimation_results = STITCHING_ESTIMATION.out[0]
    SUMMARIZE_STITCHING_POSITIONS_PER_FILE(stitching_estimation_results)
    stitching_positions_summaries = SUMMARIZE_STITCHING_POSITIONS_PER_FILE.out[0].map {
        meta, stitching_positions_summary_csv -> [meta.subMap(['output_dir', 'scene']), stitching_positions_summary_csv]
    }
    shading_corrected.map { meta, shading_corrected_zarr, metadata_yaml ->
        [meta.subMap(["output_dir", "scene"]), meta.subMap(["channel_index","channel_name"]), shading_corrected_zarr, metadata_yaml]
    }.groupTuple().join(stitching_positions_summaries).set { shading_corrected_by_output_dir_scene }

    STITCHING_EXPORT(shading_corrected_by_output_dir_scene)
    
    /* for correcting stitching positions by scenes, future work 
    stitching_estimation_results.map { meta, stitching_result_csv ->
        [meta.scene, stitching_result_csv]
    }.groupTuple().set { stitching_results_by_scene }
    stitching_results_by_scene.view()

    MEDIAN_SUMMARIZE_STITCHING_POSITIONS(stitching_results_by_scene)
    */


}

