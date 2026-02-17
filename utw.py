import subprocess
from dataclasses import dataclass
import yaml

yaml_file = 'utw_config.yaml'

@dataclass
class utw_test:
    name: str
    subp_command: list[str]
    print_forwards: list[str]

with open(yaml_file, 'r') as file:
    config = yaml.safe_load(file)

    i = 0


# class UTW:
