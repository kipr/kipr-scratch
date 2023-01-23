# kipr-scratch

A patched version of `scratch-blocks` that includes KIPR functions and is compatible with library-style packaging. A CD step automatically builds and deploys this repository under the NPM package name `@kipr/scratch-blocks`.

## Steps
  1. Generate SWIG XML bindings for `libwallaby`/`libkipr` - This step gives us a machine-readable set of function defintions from `libkipr`.
  2. Convert the SWIG XML into Blockly JS definitions - We write these out to `scratch-blocks/blocks_vertical`.
  3. Create a Default Toolbox - A default toolbox is generated from `default_toolbox.json` in conjuction with the SWIG XML definitions. This file is written out as a JS/XML blob in `scratch-blocks/blocks_vertical`.
  4. Remove unsupported Scratch blocks - We don't need (and don't support) functions like "Wait for Mouse Click".
  5. Build `scratch-blocks`
  6. Move compressed JS into the NPM package template `@kipr/scratch-blocks`
  7. Publish NPM package to private registry.

## Building

```sh
git submodule init --update
python3 build.py
```
