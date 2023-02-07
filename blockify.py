import xml.etree.ElementTree as ET
import sys
import argparse
from os import path, makedirs, getcwd

from dataclasses import dataclass
from typing import List
import json
from shutil import copyfile

@dataclass
class Parameter:
  name: str
  type: str

  def is_number(self):
    return self.type in [
      'char',
      'unsigned char',
      'int',
      'float',
      'long',
      'double',
      'unsigned int',
      'unsigned',
      'unsigned long',
      'unsigned long long',
      'unsigned short',
      'short',
      'long long',
      'size_t',
      'ssize_t',
      'ptrdiff_t',
      'int8_t',
      'int16_t',
      'int32_t',
      'int64_t',
      'uint8_t',
      'uint16_t',
      'uint32_t',
      'uint64_t'
    ]

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
module_root = root.findall('include')[1]

# Get top level includes

top_includes = module_root.findall('include')

modules = []

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
        if 'name' not in parm_attributes: continue
        parameters.append(Parameter(parm_attributes['name'], parm_attributes['type']))
    funcs.append(Function(attributes['name'], attributes['type'], parameters))
  modules.append(Module(name, funcs))

type_mappings = {
  'char': {
    'type': 'field_number',
    'min': -2**7,
    'max': 2**7 - 1,
    'precision': 1,
    'value': 0
  },
  'unsigned char': {
    'type': 'field_number',
    'min': 0,
    'max': 2**8 - 1,
    'precision': 1,
    'value': 0
  },
  'short': {
    'type': 'field_number',
    'min': -2**15,
    'max': 2**15 - 1,
    'precision': 1,
    'value': 0
  },
  'unsigned short': {
    'type': 'field_number',
    'min': 0,
    'max': 2**16 - 1,
    'precision': 1,
    'value': 0
  },
  'int': {
    'type': 'field_number',
    'min': -2**31,
    'max': 2**31 - 1,
    'precision': 1,
    'value': 0
  },
  'unsigned int': {
    'type': 'field_number',
    'min': 0,
    'max': 2**32 - 1,
    'precision': 1,
    'value': 0
  },
  'long': {
    'type': 'field_number',
    'min': -2**63,
    'max': 2**63 - 1,
    'precision': 1,
    'value': 0
  },
  'unsigned long': {
    'type': 'field_number',
    'min': 0,
    'max': 2**64 - 1,
    'precision': 1,
    'value': 0
  },
  'float': {
    'type': 'field_number',
    'min': -2**23,
    'max': 2**23 - 1,
    'precision': 0.01,
    'value': 0
  },
  'double': {
    'type': 'field_number',
    'min': -2**52,
    'max': 2**52 - 1,
    'precision': 0.01,
    'value': 0
  },
}

module_whitelist = [
  'analog',
  'digital',
  'wait_for',
  'time',
  'motor',
  'servo',
  'core',
]

overrides_json = None
with open("overrides.json", "r") as f:
  overrides_json = json.load(f)

def return_type_override(name):
  function_overrides = overrides_json.get(name)
  if function_overrides is not None:
    return_type_override = function_overrides.get('return_type')
    if return_type_override is not None:
      return return_type_override
  return None

def parameter_check_override(name, index):
  function_overrides = overrides_json.get(name)
  if function_overrides is not None:
    parameter_overrides = function_overrides.get('parameters')
    if parameter_overrides is not None:
      parameter_override = parameter_overrides.get(str(index))
      if parameter_override is not None:
        return parameter_override.get('check')
  return None

def generate_func_js(module, function):
  func_js = ''
  func_js += "Blockly.Blocks['" + module.name + "_" + function.name + "'] = {\n"
  func_js += "  init: function() {\n"
  func_js += "    this.jsonInit({\n"
  func_js += "      'message0': Blockly.Msg." + module.name.upper() + "_" + function.name.upper() + ",\n"
  func_js += "      'args0': [\n"
  i = 0
  for parameter in function.parameters:
    func_js += "        {\n"
    type_mapping = type_mappings.get(parameter.type)
    if type_mapping is None:
      print(f"Unknown type {parameter.type} for function {function.name}")
      return None
    func_js += f"          'type': 'input_value',\n"
    func_js += f"          'name': '{parameter.name.upper()}',\n"
    parameter_check = parameter_check_override(function.name, i)
    if parameter_check is not None:
      func_js += f"          'check': '{parameter_check}'\n"
    func_js += "        },\n"
    i += 1
  func_js += "      ],\n"
  func_js += f"      'category': Blockly.Categories.{module.name},\n"
  func_js += f"      'extensions': ['colours_{module.name}', '"
  return_type_o = return_type_override(function.name)
  if return_type_o is not None:
    func_js += return_type_o
  else:
    if function.return_type == 'void':
      func_js += "shape_statement"
    else:
      func_js += "output_number"
  func_js += "']\n"
  func_js += "    });\n"
  func_js += "  }\n"
  func_js += "};\n\n"
  return func_js

for module in modules:
  if module.name not in module_whitelist: continue

  # Create JS

  output_js = ''
  output_js += '"use strict";\n\n'
  output_js += f"goog.provide('Blockly.Blocks.{module.name}');\n\n"

  output_js += "goog.require('Blockly.Blocks');\n"
  output_js += "goog.require('Blockly.Colours');\n"
  output_js += "goog.require('Blockly.constants');\n"
  output_js += "goog.require('Blockly.ScratchBlocks.VerticalExtensions');\n"

  for function in module.functions:
    func_js = generate_func_js(module, function)
    if func_js is None: continue
    output_js += func_js

  with open(path.join(output_dir, module.name + '.js'), 'w') as f:
    f.write(output_js)

# Load "module_color.json" file in working directory
with open(path.join(getcwd(), 'module_colors.json')) as f:
  module_colors = json.load(f)

# Patch in colors to scratch-blocks/core/colours.js

colours_js_path = path.join('scratch-blocks', 'core', 'colours.js')
colours_js_orig = f"{colours_js_path}.orig"

# Check if colours.js.orig exists
if not path.exists(colours_js_orig):
  # Copy colours.js to colours.js.orig
  copyfile(colours_js_path, colours_js_orig)

with open(colours_js_orig) as f:
  # Insert on the 25th line
  lines = f.readlines()

  for i, line in enumerate(lines):
    if '"flyout":' in line:
      lines[i] = '  "flyout": "transparent",\n'
    if '"toolbox":' in line:
      lines[i] = '  "toolbox": "transparent",\n'
    if '"workspace":' in line:
      lines[i] = '  "workspace": "transparent",\n'


  for module in modules:
    module_color = module_colors.get(module.name)
    lines.insert(25, "'" + module.name + "': {")
    lines.insert(26, "  'primary': '" + module_color.get('primary', '#000000') + "',")
    lines.insert(27, "  'secondary': '" + module_color.get('secondary', '#000000') + "',")
    lines.insert(28, "  'tertiary': '" + module_color.get('tertiary', '#000000') + "'")
    lines.insert(29, "},")
  with open(colours_js_path, 'w') as f:
    f.writelines(lines)


# Write default_toolbox.js
output_js = ''
output_js += '"use strict";\n\n'
output_js += "goog.provide('Blockly.Blocks.defaultToolbox');\n"
output_js += "goog.require('Blockly.Blocks');\n"

output_js += "Blockly.Blocks.defaultToolbox = `\n";
output_js += '<xml id="toolbox-categories" style="display: none">\n'
for module in modules:
  if module.name not in module_whitelist: continue
  module_color = module_colors.get(module.name)
  output_js += '  <category name="' + module.name + '" id="' + module.name + '" colour="' + module_color.get('primary') + '" secondaryColour="' + module_color.get('secondary') + '">'
  for function in module.functions:
    output_js += f"    <block type=\"{module.name}_{function.name}\">\n"
    i = 0
    for parameter in function.parameters:
      output_js += f"      <value name=\"{parameter.name.upper()}\">\n"
      parameter_check = parameter_check_override(function.name, i)
      if parameter_check != 'Boolean':
        output_js += f"        <shadow type=\"math_number\">\n"
        output_js += f"          <field name=\"NUM\">0</field>\n"
        output_js += "        </shadow>\n"
      else:
        output_js += f"        <shadow type=\"logic_boolean\">\n"
        output_js += f"          <field name=\"BOOL\">TRUE</field>\n"
        output_js += "        </shadow>\n"
      output_js += "      </value>\n"
      i += 1
    output_js += "    </block>\n"
  output_js += "  </category>\n"

# Add static control category
output_js += '  <category name="%{BKY_CATEGORY_CONTROL}" id="control" colour="#FFAB19" secondaryColour="#CF8B17">'
output_js += '    <block type="control_wait" id="control_wait">'
output_js += '      <value name="DURATION">'
output_js += '        <shadow type="math_positive_number">'
output_js += '          <field name="NUM">1</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="control_repeat" id="control_repeat">'
output_js += '      <value name="TIMES">'
output_js += '        <shadow type="math_whole_number">'
output_js += '          <field name="NUM">10</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="control_forever" id="control_forever"></block>'
output_js += '    <block type="control_if" id="control_if"></block>'
output_js += '    <block type="control_if_else" id="control_if_else"></block>'
output_js += '    <block type="control_wait_until" id="control_wait_until"></block>'
output_js += '    <block type="control_repeat_until" id="control_repeat_until"></block>'
output_js += '    <block type="control_stop" id="control_stop"></block>'
output_js += '    <block type="control_start_as_clone" id="control_start_as_clone"></block>'
output_js += '    <block type="control_create_clone_of" id="control_create_clone_of">'
output_js += '      <value name="CLONE_OPTION">'
output_js += '        <shadow type="control_create_clone_of_menu"></shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="control_delete_this_clone" id="control_delete_this_clone"></block>'
output_js += '  </category>'
output_js += '  <category name="%{BKY_CATEGORY_OPERATORS}" id="operators" colour="#40BF4A" secondaryColour="#389438">'
output_js += '    <block type="operator_add" id="operator_add">'
output_js += '      <value name="NUM1">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="NUM2">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_subtract" id="operator_subtract">'
output_js += '      <value name="NUM1">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="NUM2">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_multiply" id="operator_multiply">'
output_js += '      <value name="NUM1">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="NUM2">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_divide" id="operator_divide">'
output_js += '      <value name="NUM1">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="NUM2">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_random" id="operator_random">'
output_js += '      <value name="FROM">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM">1</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="TO">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM">10</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_lt" id="operator_lt">'
output_js += '      <value name="OPERAND1">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="OPERAND2">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_equals" id="operator_equals">'
output_js += '      <value name="OPERAND1">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="OPERAND2">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_gt" id="operator_gt">'
output_js += '      <value name="OPERAND1">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="OPERAND2">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_and" id="operator_and"></block>'
output_js += '    <block type="operator_or" id="operator_or"></block>'
output_js += '    <block type="operator_not" id="operator_not"></block>'
output_js += '    <block type="operator_join" id="operator_join">'
output_js += '      <value name="STRING1">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT">hello</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="STRING2">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT">world</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_letter_of" id="operator_letter_of">'
output_js += '      <value name="LETTER">'
output_js += '        <shadow type="math_whole_number">'
output_js += '          <field name="NUM">1</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="STRING">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT">world</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_length" id="operator_length">'
output_js += '      <value name="STRING">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT">world</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_contains" id="operator_contains">'
output_js += '      <value name="STRING1">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT">hello</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="STRING2">'
output_js += '        <shadow type="text">'
output_js += '          <field name="TEXT">world</field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_mod" id="operator_mod">'
output_js += '      <value name="NUM1">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '      <value name="NUM2">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_round" id="operator_round">'
output_js += '      <value name="NUM">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '    <block type="operator_mathop" id="operator_mathop">'
output_js += '      <value name="NUM">'
output_js += '        <shadow type="math_number">'
output_js += '          <field name="NUM"></field>'
output_js += '        </shadow>'
output_js += '      </value>'
output_js += '    </block>'
output_js += '  </category>'
output_js += "</xml>\n`;\n"

with open(path.join(output_dir, 'default_toolbox.js'), 'w') as f:
  f.write(output_js)


# Write vertical_extensions.js
vertical_extensions_js_path = path.join('scratch-blocks', 'blocks_vertical', 'vertical_extensions.js')
vertical_extensions_js_orig = f"{vertical_extensions_js_path}.orig"

# Check if colours.js.orig exists
if not path.exists(vertical_extensions_js_orig):
  # Copy colours.js to colours.js.orig
  copyfile(vertical_extensions_js_path, vertical_extensions_js_orig)

with open(vertical_extensions_js_orig) as f:
  category_names = "  var categoryNames = ["
  for module in modules:
    if module.name not in module_whitelist: continue
    category_names += f"'{module.name}', "

  category_names += "'data', "
  category_names += "'data_lists', "
  category_names += "'control', "
  category_names += "'operators', "
  category_names += "'more'"
  category_names += "];\n"
  
  
  # Replace the 223rd line
  lines = f.readlines()
  lines[222] = category_names

  # Delete line 224 and 225
  lines.pop(223)
  lines.pop(223)

  with open(vertical_extensions_js_path, 'w') as f:
    f.writelines(lines)

# Open messages.js
messages_js_path = path.join('scratch-blocks', 'msg', 'messages.js')
messages_js_orig = f"{messages_js_path}.orig"

# Check if messages.js.orig exists
if not path.exists(messages_js_orig):
  # Copy messages.js to messages.js.orig
  copyfile(messages_js_path, messages_js_orig)

with open(messages_js_orig) as f:
  # append
  lines = f.readlines()
  for module in modules:
    if module.name not in module_whitelist: continue
    for function in module.functions:
      func_name = f"{function.name}("
      for parameter_index in range(0, len(function.parameters)):
        func_name += f"%{parameter_index + 1}, "
      if len(function.parameters) > 0: func_name = func_name[:-2]
      func_name += ")"
      lines.append(f"Blockly.Msg.{module.name.upper()}_{function.name.upper()} = '{func_name}';\n")
      for parameter in function.parameters:
        lines.append(f"Blockly.Msg.{module.name.upper()}_{function.name.upper()}_{parameter.name.upper()} = '{parameter.name}';\n")

  with open(messages_js_path, 'w') as f:
    f.writelines(lines)