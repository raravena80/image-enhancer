#!/usr/bin/env python3

import subprocess
import os
import signal
import sys
from datetime import datetime

class WorkerManager:
    def __init__(self, num_workers=4):
        self.num_workers = num_workers
        self.processes = []
        self.log_files = []

    def start_workers(self):
        """Start all worker processes with log redirection"""
        print(f"Starting {self.num_workers} workers...")

        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        for i in range(self.num_workers):
            worker_id = i + 1
            log_filename = f'logs/worker_{worker_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

            print(f"Starting worker {worker_id}, logging to {log_filename}")

            # Open log file
            log_file = open(log_filename, 'w')
            self.log_files.append(log_file)

            # Start worker process with stdout and stderr redirected to log file
            process = subprocess.Popen(
                ['python', 'worker.py'],
                stdout=log_file,
                stderr=subprocess.STDOUT,  # Redirect stderr to stdout (log file)
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            self.processes.append(process)
            print(f"Worker {worker_id} started with PID: {process.pid}")

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
                        log_filename = f'logs/worker_{worker_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
                        print(f"Restarting worker {worker_id}, logging to {log_filename}")

                        log_file = open(log_filename, 'w')
                        self.log_files[i] = log_file

                        new_process = subprocess.Popen(
                            ['python', 'worker.py'],
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

def signal_handler(signum, frame):
    """Handle SIGINT and SIGTERM"""
    print(f"\nReceived signal {signum}")
    sys.exit(0)

def main():
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    manager = WorkerManager(num_workers=4)

    try:
        manager.start_workers()
        manager.monitor_workers()
    except SystemExit:
        pass
    finally:
        manager.stop_workers()

if __name__ == "__main__":
    main()
