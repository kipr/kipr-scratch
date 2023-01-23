#!/bin/python3

from os import path, rename, environ
import sys
import subprocess

def is_tool(name):
  """Check whether `name` is on PATH and marked as executable."""
  from shutil import which
  return which(name) is not None

# Check that submodules are initialized
if not path.exists("libwallaby") or not path.exists("scratch-blocks"):
  print("Submodules not initialized. Run 'git submodule update --init' to initialize them.")
  exit(1)

# Check for CMake
if not is_tool("cmake"):
  print("CMake is required to build libwallaby.")
  exit(1)

# Check for Node.js
if not is_tool("node"):
  print("Node.js is required to build libwallaby.")
  exit(1)

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

blocks_vertical_path = path.join("scratch-blocks", "blocks_vertical")

for file in to_delete:
  file_path = path.join(blocks_vertical_path, file)
  if not path.exists(file_path): continue
  rename(file_path, path.join(blocks_vertical_path, file + ".old"))

# Blockify
print("Blockifying libwallaby...")
ret = subprocess.run(["python3", "blockify.py", "libwallaby-build"])

# Generate new default toolbox
print("Generating new default toolbox...")


# Install scratch-blocks dependencies
print("Installing scratch-blocks dependencies...")
ret = subprocess.run(["npm", "install"], cwd="scratch-blocks")
if ret.returncode != 0:
  print("Failed to install scratch-blocks dependencies.")
  exit(1)

# Build scratch-blocks
print("Building scratch-blocks...")
ret = subprocess.run(["node", "build.py"], cwd="scratch-blocks")
if ret.returncode != 0:
  print("Failed to build scratch-blocks.")
  exit(1)

