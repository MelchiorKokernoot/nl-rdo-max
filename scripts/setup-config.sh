#!/bin/bash

set -e

copy_example_config () {
  if [[ ! -f $1 ]]; then
    echo "copying $1.exapmle to $1"
    cp "$1.example" $1
  fi
}

copy_example_config "max.conf"
copy_example_config "clients.json"
copy_example_config "saml/tvs/settings.json"
