#!/usr/bin/env python3

import subprocess
import os
import signal
import sys
import argparse
from datetime import datetime

class WorkerManager:
    def __init__(self, num_workers=4, show_logs=False, stagger_start=0.5):
        self.num_workers = num_workers
        self.show_logs = show_logs
        self.stagger_start = stagger_start
        self.processes = []
        self.log_files = []
        # Get the directory where this script is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.worker_path = os.path.join(self.script_dir, 'worker.py')
        self.logs_dir = os.path.join(self.script_dir, 'logs')

    def start_workers(self):
        """Start all worker processes with log redirection"""
        print(f"Starting {self.num_workers} workers...")

        # Create logs directory if it doesn't exist (relative to script location)
        os.makedirs(self.logs_dir, exist_ok=True)

        for i in range(self.num_workers):
            worker_id = i + 1
            log_filename = os.path.join(self.logs_dir, f'worker_{worker_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

            print(f"Starting worker {worker_id}, logging to {log_filename}")

            # Open log file
            log_file = open(log_filename, 'w')
            self.log_files.append(log_file)

            # Start worker process with stdout and stderr redirected to log file
            if self.show_logs:
                # Use a custom class to write to both file and stdout
                import threading

                # ANSI color codes for different workers
                colors = [
                    '\033[91m',  # Red
                    '\033[92m',  # Green
                    '\033[93m',  # Yellow
                    '\033[94m',  # Blue
                    '\033[95m',  # Magenta
                    '\033[96m',  # Cyan
                    '\033[97m',  # White
                    '\033[90m',  # Gray
                ]
                reset_color = '\033[0m'
                worker_color = colors[(worker_id - 1) % len(colors)]

                class TeeOutput:
                    def __init__(self, file, stdout, worker_id, color):
                        self.file = file
                        self.stdout = stdout
                        self.worker_id = worker_id
                        self.color = color
                        self.reset = reset_color

                    def write(self, data):
                        self.file.write(data)
                        self.stdout.write(f"{self.color}[Worker {self.worker_id}]{self.reset} {data}")
                        self.file.flush()
                        self.stdout.flush()

                    def flush(self):
                        self.file.flush()
                        self.stdout.flush()

                tee_output = TeeOutput(log_file, sys.stdout, worker_id, worker_color)

                process = subprocess.Popen(
                    ['python', self.worker_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                    text=True
                )

                # Start a thread to handle the output - fix closure issue by capturing worker_id
                def handle_output(tee_out, proc):
                    for line in proc.stdout:
                        tee_out.write(line)

                output_thread = threading.Thread(target=handle_output, args=(tee_output, process), daemon=True)
                output_thread.start()
            else:
                process = subprocess.Popen(
                    ['python', self.worker_path],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,  # Redirect stderr to stdout (log file)
                    bufsize=1,  # Line buffered
                    universal_newlines=True
                )

            self.processes.append(process)
            print(f"Worker {worker_id} started with PID: {process.pid}")

            # Stagger worker starts to reduce initial task conflicts
            if worker_id < self.num_workers:  # Don't wait after the last worker
                import time
                time.sleep(self.stagger_start)

    def stop_workers(self):
        """Stop all worker processes gracefully"""
        print("\nStopping all workers...")

        for i, process in enumerate(self.processes):
            worker_id = i + 1
            if process.poll() is None:  # Process is still running
                print(f"Stopping worker {worker_id} (PID: {process.pid})")
                process.terminate()

                # Wait up to 5 seconds for graceful shutdown
                try:
                    process.wait(timeout=5)
                    print(f"Worker {worker_id} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"Worker {worker_id} didn't stop gracefully, forcing kill")
                    process.kill()
                    process.wait()
            else:
                print(f"Worker {worker_id} already stopped")

        # Close log files
        for log_file in self.log_files:
            log_file.close()

        print("All workers stopped")

    def monitor_workers(self):
        """Monitor workers and restart if they crash"""
        print("Monitoring workers... Press Ctrl+C to stop")

        try:
            while True:
                # Check if any worker has died
                for i, process in enumerate(self.processes):
                    if process.poll() is not None:  # Process has terminated
                        worker_id = i + 1
                        print(f"Worker {worker_id} died with return code {process.returncode}")

                        # Close old log file
                        self.log_files[i].close()

                        # Restart worker
                        log_filename = os.path.join(self.logs_dir, f'worker_{worker_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
                        print(f"Restarting worker {worker_id}, logging to {log_filename}")

                        log_file = open(log_filename, 'w')
                        self.log_files[i] = log_file

                        if self.show_logs:
                            import threading

                            # ANSI color codes for different workers
                            colors = [
                                '\033[91m',  # Red
                                '\033[92m',  # Green
                                '\033[93m',  # Yellow
                                '\033[94m',  # Blue
                                '\033[95m',  # Magenta
                                '\033[96m',  # Cyan
                                '\033[97m',  # White
                                '\033[90m',  # Gray
                            ]
                            reset_color = '\033[0m'
                            worker_color = colors[(worker_id - 1) % len(colors)]

                            class TeeOutput:
                                def __init__(self, file, stdout, worker_id, color):
                                    self.file = file
                                    self.stdout = stdout
                                    self.worker_id = worker_id
                                    self.color = color
                                    self.reset = reset_color

                                def write(self, data):
                                    self.file.write(data)
                                    self.stdout.write(f"{self.color}[Worker {self.worker_id}]{self.reset} {data}")
                                    self.file.flush()
                                    self.stdout.flush()

                                def flush(self):
                                    self.file.flush()
                                    self.stdout.flush()

                            tee_output = TeeOutput(log_file, sys.stdout, worker_id, worker_color)

                            new_process = subprocess.Popen(
                                ['python', self.worker_path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                bufsize=1,
                                universal_newlines=True,
                                text=True
                            )

                            def handle_output(tee_out, proc):
                                for line in proc.stdout:
                                    tee_out.write(line)

                            output_thread = threading.Thread(target=handle_output, args=(tee_output, new_process), daemon=True)
                            output_thread.start()
                        else:
                            new_process = subprocess.Popen(
                                ['python', self.worker_path],
                                stdout=log_file,
                                stderr=subprocess.STDOUT,
                                bufsize=1,
                                universal_newlines=True
                            )

                        self.processes[i] = new_process
                        print(f"Worker {worker_id} restarted with PID: {new_process.pid}")

                # Wait a bit before next check
                import time
                time.sleep(2)

        except KeyboardInterrupt:
            print("\nReceived stop signal")

def signal_handler(signum, _frame):
    """Handle SIGINT and SIGTERM"""
    print(f"\nReceived signal {signum}")
    sys.exit(0)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Start and manage Temporal workers')
    parser.add_argument('--workers', '-w', type=int, default=4,
                        help='Number of workers to start (default: 2, reduced to minimize task conflicts)')
    parser.add_argument('--show-logs', action='store_true',
                        help='Display logs to stdout as well as files')
    parser.add_argument('--stagger-start', type=float, default=0.5,
                        help='Seconds to wait between starting each worker (default: 0.5)')
    args = parser.parse_args()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    manager = WorkerManager(num_workers=args.workers, show_logs=args.show_logs, stagger_start=args.stagger_start)

    try:
        manager.start_workers()
        manager.monitor_workers()
    except SystemExit:
        pass
    finally:
        manager.stop_workers()

if __name__ == "__main__":
    main()
