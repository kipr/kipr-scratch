from shutil import copyfile
from os import path, makedirs, getcwd
import json
from distutils.dir_util import copy_tree


scratch_blocks_path = "scratch-blocks"
kipr_scratch_path = "kipr-scratch"

makedirs(kipr_scratch_path, exist_ok=True)

copyfile(
  path.join(scratch_blocks_path, "blockly_compressed_vertical.js"),
  path.join(kipr_scratch_path, "blockly_compressed_vertical.js")
)

copyfile(
  path.join(scratch_blocks_path, "blocks_compressed_vertical.js"),
  path.join(kipr_scratch_path, "blocks_compressed_vertical.js")
)

copyfile(
  path.join(scratch_blocks_path, "blocks_compressed.js"),
  path.join(kipr_scratch_path, "blocks_compressed.js")
)

copyfile(
  path.join(scratch_blocks_path, "msg", "messages.js"),
  path.join(kipr_scratch_path, "messages.js")
)

copyfile(
  path.join(scratch_blocks_path, "msg", "scratch_msgs.js"),
  path.join(kipr_scratch_path, "scratch_msgs.js")
)

copy_tree(
  path.join(scratch_blocks_path, "media"),
  path.join(kipr_scratch_path, "media")
)

# Write package.json

package_json = {
  "name": "kipr-scratch",
  "version": "1.0.0",
  "description": "KIPR's fork of Scratch 3.0",
}

with open(path.join(kipr_scratch_path, "package.json"), "w") as f:
  f.write(json.dumps(package_json, indent=2))