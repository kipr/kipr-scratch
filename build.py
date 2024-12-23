#!/bin/python3

from os import path, rename, environ, chdir, getcwd

import sys
import subprocess
from shutil import which
import json

def is_tool(name):
  """Check whether `name` is on PATH and marked as executable."""
  return which(name) is not None

# Check that submodules are initialized
if not path.exists("libwallaby") or not path.exists("scratch-blocks"):
  print("Submodules not initialized. Run 'git submodule update --init' to initialize them.")
  exit(1)

# Check for CMake
if not is_tool("cmake"):
  print("CMake is required to build libwallaby.")
  exit(1)

if not is_tool('java'):
  print('Java is required to build scratch-blocks.')
  exit(1)

# Check for Node.js
if not is_tool("node"):
  print("Node.js is required to build libwallaby.")
  exit(1)

# Check node version
ret = subprocess.run(['node', '-v'], capture_output=True)
version_str = ret.stdout.decode()

node_major_version = int(version_str.strip()[1:3])

# Get additional CMake arguments
cmake_args = []

# Check LIBWALLABY_CMAKE_ARGS environment variable
if "LIBWALLABY_CMAKE_ARGS" in environ:
  cmake_args = environ["LIBWALLABY_CMAKE_ARGS"].split(";")

cmake_args.append("-Dwith_camera=OFF")
cmake_args.append("-Dwith_graphics=OFF")
cmake_args.append("-Dwith_tello=OFF")
cmake_args.append("-Dwith_python_binding=OFF")
cmake_args.append("-Dwith_xml_binding=ON")
cmake_args.append("-DDUMMY=ON")
cmake_args.append("-Dwith_tests=OFF")
cmake_args.append("-Slibwallaby")
cmake_args.append("-Blibwallaby-build")

# Build libwallaby
print('Configuring libwallaby...')
ret = subprocess.run(["cmake"] + cmake_args)
if ret.returncode != 0:
  print("Failed to configure libwallaby.")
  exit(1)

print('Building libwallaby...')
ret = subprocess.run(["cmake", "--build", "libwallaby-build"])
if ret.returncode != 0:
  print("Failed to build libwallaby.")
  exit(1)

# Delete unnecessary blocks from scratch-blocks
print("Deleting unnecessary blocks from scratch-blocks...")
to_delete = [
  'event.js',
  'extensions.js',
  'default_toolbox.js',
  'looks.js',
  'motion.js',
  'sensing.js',
  'sound.js'
]

python3 = 'python3'
if is_tool('python3.12'):
  python3 = 'python3.12'
elif is_tool('python3.11'):
  python3 = 'python3.11'
elif is_tool('python3.10'):
  python3 = 'python3.10'
elif is_tool('python3.9'):
  python3 = 'python3.9'
elif is_tool('python3.8'):
  python3 = 'python3.8'
elif is_tool('python3.7'):
  python3 = 'python3.7'
else:
  print('Warning: Python 3.7+ could not be found. Using `python3`. This might not work.')

blocks_vertical_path = path.join("scratch-blocks", "blocks_vertical")

for file in to_delete:
  file_path = path.join(blocks_vertical_path, file)
  if not path.exists(file_path): continue
  rename(file_path, path.join(blocks_vertical_path, file + ".old"))

# Blockify
print("Blockifying libwallaby...")
ret = subprocess.run([python3, "blockify.py", "libwallaby-build", "scratch-blocks/blocks_vertical"])



# Install and build scratch-blocks dependencies
scratch_blocks_node_modules_bin = path.join(getcwd(), "scratch-blocks", "node_modules", ".bin")
npm_env = {
  'PATH': f"{scratch_blocks_node_modules_bin}:{environ['PATH']}",
}

if node_major_version >= 17:
  npm_env['NODE_OPTIONS'] = '--openssl-legacy-provider'


# Run without scripts to skip the prepublish script
# We need to run prepublish steps separately so we can specifically use python3
print("Running 'npm install' for scratch-blocks...")
ret = subprocess.run(["npm", "install", "--ignore-scripts"], cwd="scratch-blocks")
if ret.returncode != 0:
  print("Failed to run 'npm install' for scratch-blocks.")
  exit(1)

print("Building scratch-blocks...")
ret = subprocess.run([python3, "build.py"], cwd="scratch-blocks", env=npm_env)
if ret.returncode != 0:
  print("Failed to build scratch-blocks.")
  exit(1)

print("Webpacking scratch-blocks...")
ret = subprocess.run(["webpack"], cwd="scratch-blocks", env=npm_env)
if ret.returncode != 0:
  print("Failed to webpack scratch-blocks.")
  exit(1)
