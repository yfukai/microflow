#!/usr/bin/env python3
import yaml

with open('metadata.yaml', 'r') as f:
    metadata = yaml.safe_load(f)
    
exported_data = []
for scene, scene_data in metadata.items():
    channel_names = scene_data.get('channel_names', [])
    for idx, name in enumerate(channel_names):
        exported_data.append({
            'scene': scene,
            'channel_index': idx,
            'channel_name': name
        })
print(yaml.dump(exported_data))