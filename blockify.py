import xml.etree.ElementTree as ET
import sys
import argparse
from os import path, makedirs

from dataclasses import dataclass
from typing import List

@dataclass
class Parameter:
  name: str
  type: str

@dataclass
class Function:
  name: str
  return_type: str
  parameters: List[Parameter]

@dataclass
class Module:
  name: str
  functions: List[Function]

parser = argparse.ArgumentParser(description='Generate Blockly JS bindings from SWIG XML bindings')

parser.add_argument(
  'build_root',
  help='The root directory of the libwallaby build'
)

parser.add_argument(
  'output_dir',
  help='The JS directory to output to'
)

args = parser.parse_args()

build_root = args.build_root
output_dir = args.output_dir

if not path.exists(output_dir):
  makedirs(output_dir)

xml_binding_path = path.join(build_root, "binding", "xml", "kipr.xml")

tree = None
with open(xml_binding_path, "r") as f:
  tree = ET.parse(f)

def attributelist(node):
  if node.tag != 'attributelist':
    node = node.find('attributelist')
  ret = dict()
  attributes = node.findall('attribute')
  for attribute in attributes:
    ret[attribute.get('name')] = attribute.get('value')
  return ret

def generate_js(functions):
  'test'

root = tree.getroot()

# The XML spec is as follows:
# Each binding file is an `include` under the `module` node
# Each binding `include` then (generally) has a child `include` that points to the real H file
# The real H file `include` has a list of `cdecl` nodes, each of which is a function

# Get module
module = root.findall('include')[1]

# Get top level includes

top_includes = module.findall('include')

print(len(top_includes))

for top_include in top_includes:
  # Get the real H file
  h_file = top_include.find('include')

  if h_file is None: continue

  attributes = attributelist(h_file)
  
  # Get name from path and remove .h
  name = path.basename(attributes['name'])[:-2]

  # Get the list of functions
  functions = h_file.findall('cdecl')

  funcs = []

  for function in functions:
    attributes = attributelist(function)
    parameters = []
    parmlist = function.find('attributelist').find('parmlist')
    if parmlist is not None:
      for parm in parmlist.findall('parm'):
        parm_attributes = attributelist(parm)
        if name not in parm_attributes: continue
        parameters.append(Parameter(parm_attributes['name'], parm_attributes['type']))
    funcs.append(Function(attributes['name'], attributes['type'], parameters))

  print(Module(name, funcs))


