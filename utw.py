import subprocess
from dataclasses import dataclass
import yaml
import threading
from loguru import logger

yaml_file = 'utw_config.yaml'

@dataclass
class utw_test:
    name: str
    subp_command: list[str]
    print_forwards: list[str]

with open(yaml_file, 'r') as file:
    config = yaml.safe_load(file)

    i = 0


class UTW:
    def __init__(self, config_file: str = "/home/admin/lake_tests/utw_config.yaml"):
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)

        self.UTW_TEST: utw_test | None = None

        self.test_process: subprocess.Popen | None = None

    def setup_test(self, test: str):
        if self.UTW_TEST is not None:
            raise ValueError("A test is already set up. Please reset before setting up a new test.")
        if self.test_process is not None:
            raise ValueError("A test process is already running. Please reset before setting up a new test.")
        
        # Right now, we might have a role with the test string; check for the ';' symbol
        # TODO: In the future, we might add a second ';' for additional arguments
        if ';' in test:
            test_name, role = test.split(';')
        else:
            test_name = test
            role = None
        
        if test_name not in self.config.keys():
            raise ValueError(f"Test '{test_name}' not found in configuration.")
        if role is not None and not 'roles' in self.config[test_name].keys():
            raise ValueError(f"Test '{test_name}' does not have any roles defined, but role '{role}' was specified.")
        if role is not None and role not in self.config[test_name]['roles']:
            raise ValueError(f"Role '{role}' not found in test '{test_name}' configuration.")
        if role is None and 'roles' in self.config[test_name].keys():
            raise ValueError(f"Test '{test_name}' has roles defined, but no role was specified.")
        
        test_config = self.config[test_name]

        # Start up the subprocess command list
        subp_com = ["python3", test_config["py_exe"]]

        # If there are any arguments for the role, add them to the subprocess command list
        if "args" in test_config.keys():
            args = test_config["args"]
            if not isinstance(args, list):
                raise TypeError(f"Expected a list for 'args' in test '{test_name}', got {type(args).__name__}")
            subp_com.extend(args)
        elif role is not None and "args" in test_config["roles"][role].keys():
            args = test_config["roles"][role]["args"]
            if not isinstance(args, list):
                raise TypeError(f"Expected a list for 'args' in role '{role}' of test '{test_name}', got {type(args).__name__}")
            subp_com.extend(args)

        print_fwd = None

        # There might be log forwards in the test config, or they might be in the role config, but not both
        if "log_forward" in test_config.keys():
            p_fwd = test_config["log_forward"]
            if not isinstance(p_fwd, list):
                raise TypeError(f"Expected a list for 'log_forward' in test '{test_name}', got {type(p_fwd).__name__}")
            print_fwd = p_fwd
        elif role is not None and "log_forward" in test_config["roles"][role].keys():
            p_fwd = test_config["roles"][role]["log_forward"]
            if not isinstance(p_fwd, list):
                raise TypeError(f"Expected a list for 'log_forward' in role '{role}' of test '{test_name}', got {type(p_fwd).__name__}")
            print_fwd = p_fwd

        self.UTW_TEST = utw_test(
            name = f"{test_name};{role}" if role is not None else test_name,
            subp_command = subp_com,
            print_forwards = print_fwd
        )

        return f"Test '{self.UTW_TEST.name}' set up successfully."

        




        