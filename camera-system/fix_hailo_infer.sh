#!/bin/bash
# Quick fix for Hailo inference API on RPi
# Run this on the Raspberry Pi

cd ~/camera-system/agents

# Fix the detect method in inference_agent_hailo.py
python3 << 'PYEOF'
import re

# Read the file
with open('inference_agent_hailo.py', 'r') as f:
    content = f.read()

# Fix the InferVStreams usage - change .input to .input_vstreams
old_code = "input_dict = {list(infer_pipeline.input.keys())[0]: input_data}"
new_code = "input_dict = {list(infer_pipeline.input_vstreams.keys())[0]: input_data}"

content = content.replace(old_code, new_code)

# Write back
with open('inference_agent_hailo.py', 'w') as f:
    f.write(content)

print("✅ Fixed InferVStreams API")
PYEOF

echo "Done!"
