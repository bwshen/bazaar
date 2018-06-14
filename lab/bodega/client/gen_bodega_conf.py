#!/usr/bin/env python
"""Generate bodega conf."""

import argparse
import yaml

argparser = argparse.ArgumentParser('Generate a bodega conf.yml')
argparser.add_argument('--path', type=str, required=True)
argparser.add_argument('--token', type=str, required=True)
args = argparser.parse_args()

with open(args.path, 'w') as f:
    yaml.dump({'url': 'https://bodega.rubrik-lab.com/api/',
               'token': args.token},
              f,
              default_flow_style=False)
