#!/usr/bin/env python3
import yaml

with open('metadata.yaml', 'r') as f:
    metadata = yaml.safe_load(f)
    
exported_data = []
for scene, scene_data in metadata.items():
    # The unique names are used so that each channel can be identified by its name,
    # e.g. when selecting the target channel of the stitching estimation.
    channel_names = scene_data.get('unique_channel_names', [])
    for idx, name in enumerate(channel_names):
        exported_data.append({
            'scene': scene,
            'channel_index': idx,
            'channel_name': name
        })
print(yaml.dump(exported_data))