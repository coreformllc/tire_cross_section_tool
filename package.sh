#! /bin/bash

curr_dir=$(dirname "$(realpath "$0")")
echo "Generating toolbar file for directory: ${curr_dir}"
sed "s|@TOOLBAR_INSTALL_DIR@|${curr_dir}|g" "${curr_dir}/toolbars/template.tmpl" > toolbars/tire_cross_section_tool.ttb

sed "s|@TOOLBAR_INSTALL_DIR@|${curr_dir}|g" "${curr_dir}/mappings.tmpl" > .mappings
tar czvf tire_cross_section_tool.tar.gz scripts toolbars/tire_cross_section_tool.ttb icons .mappings

rm toolbars/tire_cross_section_tool.ttb
rm .mappings
