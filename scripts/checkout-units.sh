#!/usr/bin/env bash
# Run from the workspace containing the sibling repository checkouts.
set -euo pipefail
required_units=(anth es puba soc ssri)
optional_units=(geo pols psy sci wgss)
for unit in "${required_units[@]}"; do
  GIT_TERMINAL_PROMPT=0 git clone --depth 1 "https://github.com/cssweb-stack/${unit}.git" "$unit"
  if [[ ! -d "$unit/src" ]]; then
    echo "::error::Required Review source ${unit}/src is missing."
    exit 1
  fi
done
for unit in "${optional_units[@]}"; do
  if ! GIT_TERMINAL_PROMPT=0 git clone --depth 1 "https://github.com/cssweb-stack/${unit}.git" "$unit"; then
    echo "::warning::Optional Review source ${unit} is unavailable; its review listings will be omitted."
  fi
done
