# this script is used to manage GNU Radio processes using Python's subprocess module.
# It provides a class GNURadioManager that can start, poll, and stop a GNU Radio process.
# this is needed because gnuradio needs to run in a different conda environment 


import subprocess
import threading
import time

class GNURadioManager:
    def __init__(self, conda_env, path, python_filename, read_stdout=False, read_stderr=False, **kwargs):
        self.conda_env = conda_env
        self.path = path
        self.python_filename = python_filename
        self.read_stdout = read_stdout
        self.read_stderr = read_stderr
        self.kwargs = kwargs
        self.process = None
        self.pid = None
        self.stdout_thread = None
        self.stderr_thread = None
        self._stop_threads = threading.Event()

    def _build_command(self):
        kwargs_string = ' '.join(f"--{key} {value}" for key, value in self.kwargs.items()) if self.kwargs else ''
        full_command_string = f"{kwargs_string}".strip()
        print("Command kwargs:", full_command_string)

        command = (
            f"bash -c 'source ~/radioconda/etc/profile.d/conda.sh && "
            f"conda activate {self.conda_env} && "
            f"cd {self.path} && "
            f"python {self.python_filename} {full_command_string}'"
        )
        print("Command:\n", command)
        return command

    def _read_output(self, pipe, pipe_name):
        while not self._stop_threads.is_set():
            line = pipe.readline()
            if line:
                print(f"{pipe_name}: {line.strip()}")
            elif self.process.poll() is not None:
                break
        pipe.close()

    def start(self):
        command = self._build_command()
        try:
            self.process = subprocess.Popen(
                command, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.pid = self.process.pid
            print("Process started with PID:", self.process.pid)

            # Start threads to read stdout and stderr if required
            if self.read_stdout:
                self.stdout_thread = threading.Thread(target=self._read_output, args=(self.process.stdout, "STDOUT"))
                self.stdout_thread.start()

            if self.read_stderr:
                self.stderr_thread = threading.Thread(target=self._read_output, args=(self.process.stderr, "STDERR"))
                self.stderr_thread.start()
        except Exception as e:
            print("Error occurred while starting subprocess:", e)

    def poll(self):
        if self.process is None:
            print("No process to poll.")
            return None

        return_code = self.process.poll()
        if return_code is None:
            print("Process is still running.")
        else:
            print("Process finished with return code:", return_code)
        return return_code

    def stop(self):
        if self.process is None:
            print("No process to stop.")
            return

        self._stop_threads.set()
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
            print(f"Process {self.pid} terminated successfully.")
        except subprocess.TimeoutExpired:
            self.process.kill()
            print("Process killed after timeout.")
        finally:
            self.process = None
            self.pid = None

            # Wait for threads to finish if they were started
            if self.stdout_thread:
                self.stdout_thread.join()

            if self.stderr_thread:
                self.stderr_thread.join()

# Example usage
if __name__ == "__main__":
    conda_env = "radio_base"
    path = "/home/sunlab/radioconda/share/gnuradio/examples/ieee802_11"
    python_filename = "wifi_transceiver_nogui.py"

    manager = GNURadioManager(conda_env, path, python_filename, read_stdout=True, read_stderr=True)
    manager.start()

    time.sleep(5)  # Wait for a while before polling

    poll_limit = 20  # Poll for X seconds

    while poll_limit:
        return_code = manager.poll()
        if return_code is not None:
            print("Process finished.")
            print("Return code:", return_code)
            break
        time.sleep(1)  # Poll every second
        poll_limit -= 1
        print(f"Polling limit: {poll_limit}")

    manager.stop()
