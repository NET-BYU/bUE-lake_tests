import subprocess
from dataclasses import dataclass
import yaml
import threading
# from loguru import logger
import queue

yaml_file = 'utw_config.yaml'

@dataclass
class utw_test:
    name: str
    subp_command: list[str]
    print_forwards: list[str]


class Utw:
    def __init__(self, config_file: str = "/home/admin/lake_tests/utw_config.yaml"):
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)

        self.UTW_TEST: utw_test | None = None

        self.test_process: subprocess.Popen | None = None

        # Create a thread to read the output of the subprocess
        self.read_thread = threading.Thread(target=self._read_output, daemon=True)
        self.outputs_queue = queue.Queue()

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
    
    def run_test(self):
        if self.UTW_TEST is None:
            raise ValueError("No test set up. Please set up a test before running.")
        if self.test_process is not None:
            raise ValueError("A test process is already running. Please reset before running a new test.")
        
        try:
            self.test_process = subprocess.Popen(
                self.UTW_TEST.subp_command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                bufsize=1,  # Line-buffered
                universal_newlines=True,  # Text mode, also enables line buffering
                text=True,  # decode bytes to str
                encoding="utf-8",
                errors="replace",
            )
            self.outputs_queue.put(f"Started test '{self.UTW_TEST.name}' with PID {self.test_process.pid}.")
        except Exception as e:
            self.outputs_queue.put(f"Failed to start test '{self.UTW_TEST.name}': {e}")
            self.test_process = None
            return
        
        self.read_thread.start()

    def _read_output(self):
        if self.test_process is None:
            # logger.error("No test process to read from.")
            self.outputs_queue.put("No test process to read from.")
            return
        
        while self.test_process.poll() is None:  # While the process is still running
            try:
                for line in self.test_process.stdout:
                    line = line.strip()
                    if any(fwd in line for fwd in self.UTW_TEST.print_forwards):
                        self.outputs_queue.put(f"[{self.UTW_TEST.name}] {line}")
            except Exception as e:
                self.outputs_queue.put(f"Error reading output from test '{self.UTW_TEST.name}': {e}")

    def reset_test(self):
        if self.test_process is not None:
            self.test_process.terminate()
            self.test_process.wait()
            self.outputs_queue.put(f"Terminated test '{self.UTW_TEST.name}'.")
            self.test_process = None
            self.read_thread.join(timeout=1)  # Wait for the reading thread to finish
        else:
            self.outputs_queue.put("No test process to terminate.")
        
        self.UTW_TEST = None

    def get_output(self):
        outputs = []
        while not self.outputs_queue.empty():
            outputs.append(self.outputs_queue.get())
        return outputs
    
    def get_test_status(self):
        if self.test_process is None:
            return False, f"No test process running for test '{self.UTW_TEST.name}'." \
                if self.UTW_TEST else "No test process running."
        if self.test_process.poll() is None:
            return True, f"Test '{self.UTW_TEST.name}' is running."
      