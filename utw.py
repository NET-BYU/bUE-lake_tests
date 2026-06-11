import subprocess
from dataclasses import dataclass
import yaml
import threading
from loguru import logger
import queue
import signal

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

    def setup_test(self, test: str) -> bool:
        if self.UTW_TEST is not None:
            raise ValueError("A test is already set up. Please reset before setting up a new test.")
        if self.test_process is not None:
            raise ValueError("A test process is already running. Please reset before setting up a new test.")
        
        try:
            test_name, role, ui_args = test.split(';')
        except ValueError:
            return False
        
        # Make sure test_name is in the config and role is in the test config
        if test_name not in self.config.keys():
            raise ValueError(f"Test '{test_name}' not found in configuration.")
        if role not in self.config[test_name].keys():
            raise ValueError(f"Role '{role}' not found in test '{test_name}' configuration.")
        
        test_config = self.config[test_name][role]

        test_command = ["python3"]

        test_command.append(test_config["py_exe"])

        if "exe_args" in test_config.keys():
            exe_args = test_config["exe_args"]
            if not isinstance(exe_args, list):
                raise TypeError(f"Expected a list for 'exe_args' in role '{role}' of test '{test_name}', got {type(exe_args).__name__}")
            test_command.extend(exe_args)

        # Now, see if ui_args are in the test config, and if so, add them to the test command
        if ui_args != "":
            for i, arg in enumerate(ui_args.split(",")):
                if arg == '':
                    continue
                exe_arg = f"--{list(test_config['ui_args'].keys())[i]}={arg.strip()}"
                test_command.append(exe_arg)

        print_fwd = None

        # There might be log forwards in the test config, or they might be in the role config, but not both
        if "log_forward" in test_config.keys():
            p_fwd = test_config["log_forward"]
            if not isinstance(p_fwd, list):
                raise TypeError(f"Expected a list for 'log_forward' in test '{test_name}', got {type(p_fwd).__name__}")
            print_fwd = p_fwd

        self.UTW_TEST = utw_test(
            name = f"{test_name};{role}",
            subp_command = test_command,
            print_forwards = print_fwd
        )

        return True
    
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
            return False
        
        self.read_thread.start()
        return True

    def _read_output(self):
        if self.test_process is None:
            # logger.error("No test process to read from.")
            self.outputs_queue.put("No test process to read from.")
            return
        
        while self.test_process.poll() is None:  # While the process is still running
            try:
                for line in self.test_process.stdout:
                    line = line.strip()
                    if self.UTW_TEST.print_forwards is not None:
                        if any(fwd in line for fwd in self.UTW_TEST.print_forwards):
                            self.outputs_queue.put(f"[{self.UTW_TEST.name}] {line}")
                    # else:
                    #     self.outputs_queue.put(f"[{self.UTW_TEST.name}] {line}")
            except Exception as e:
                logger.error(f"Error reading output from test '{self.UTW_TEST.name}': {e}")

    def reset_test(self):
        if self.test_process is not None:
            self.test_process.terminate()
            self.test_process.wait()
            self.read_thread.join(timeout=1)  # Wait for the reading thread to finish
            self.outputs_queue.put(f"Terminated test '{self.UTW_TEST.name}'.")
            self.test_process = None
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
            # self.outputs_queue.put("Error: Check on empty test process.")
            return False, None
        else:
            return True, self.test_process.poll()

    def cancel_test(self):
        if self.test_process is not None:
            self.test_process.send_signal(signal.SIGINT)  # Send SIGINT to allow graceful shutdown
            self.outputs_queue.put(f"Sent cancel signal to test '{self.UTW_TEST.name}'.")
        else:
            self.outputs_queue.put("No test process to cancel.")
      