import os
import sys
import time
import subprocess

# Path to Vibe Code Helper
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VIBE_HELPER_PATH = os.path.join(SCRIPT_DIR, "vibe_code_helper.py")

# Check interval in seconds
CHECK_INTERVAL = 5

# Log file
LOG_FILE = os.path.join(SCRIPT_DIR, "watcher_log.txt")


def log(message):
    """Write a message to the log file with timestamp."""
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    except Exception:
        pass


def is_another_watcher_running():
    """Check if another instance of this watcher is already running."""
    try:
        current_pid = os.getpid()
        result = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'", "get", "ProcessId,CommandLine"],
            capture_output=True,
            text=True,
            check=False,
        )
        own_path = os.path.abspath(__file__).lower()
        count = 0
        for line in result.stdout.splitlines():
            if own_path in line.lower():
                parts = line.split()
                if parts and parts[-1].isdigit() and int(parts[-1]) != current_pid:
                    count += 1
        return count > 0
    except Exception:
        return False


def is_windsurf_running():
    """Check if Windsurf is currently running."""
    try:
        # Check process names first
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq windsurf.exe"],
            capture_output=True,
            text=True,
            check=False,
        )
        if "windsurf.exe" in result.stdout.lower():
            return True

        # Also check command lines for windsurf (in case it runs as Code.exe)
        result = subprocess.run(
            ["wmic", "process", "get", "CommandLine"],
            capture_output=True,
            text=True,
            check=False,
        )
        return "windsurf" in result.stdout.lower()
    except Exception:
        return False


def is_vibe_helper_running():
    """Check if Vibe Code Helper is already running."""
    try:
        result = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'", "get", "CommandLine"],
            capture_output=True,
            text=True,
            check=False,
        )
        return VIBE_HELPER_PATH.lower() in result.stdout.lower()
    except Exception:
        return False


def launch_vibe_helper():
    """Launch Vibe Code Helper without console window."""
    try:
        python_dir = os.path.dirname(sys.executable)
        pythonw_path = os.path.join(python_dir, "pythonw.exe")
        python_path = pythonw_path if os.path.exists(pythonw_path) else sys.executable

        subprocess.Popen(
            [python_path, VIBE_HELPER_PATH],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        log("Vibe Code Helper launched.")
    except Exception as e:
        log(f"Failed to launch Vibe Code Helper: {e}")


def main():
    """Watch for Windsurf and launch Vibe Code Helper when it opens."""
    log(f"Watcher starting with PID {os.getpid()}")

    if is_another_watcher_running():
        log("Another watcher already running. Exiting.")
        return

    # Initialize with current Windsurf state so we don't launch if it's already running
    windsurf_was_running = is_windsurf_running()
    log(f"Watcher started. Initial Windsurf state: {windsurf_was_running}")

    while True:
        windsurf_running = is_windsurf_running()
        log(f"Windsurf running: {windsurf_running}, was_running: {windsurf_was_running}")

        if windsurf_running and not windsurf_was_running:
            log("Windsurf opened. Launching Vibe Code Helper...")
            if not is_vibe_helper_running():
                launch_vibe_helper()
            else:
                log("Vibe Code Helper is already running.")

        windsurf_was_running = windsurf_running
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
