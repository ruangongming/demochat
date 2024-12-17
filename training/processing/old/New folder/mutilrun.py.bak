import subprocess
import logging
import os
import gc
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Cấu hình logging để ghi vào file và console
LOG_FILE = os.path.join('logs', 'multirun_log.log')
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)


def run_script(script_name):
    """Chạy một script và ghi lại kết quả."""
    logging.info(f"Running {script_name}...")
    try:
        result = subprocess.run([sys.executable, script_name], check=True)
        logging.info(f"Finished running {script_name}.")
        return None
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to run {script_name}. Error: {e}")
        return e


def main():
    """Chạy tất cả các script trong danh sách."""
    # scripts = ['db.py', 'raw.py', 'scraper.py', 'vectordb.py']
    scripts = ['db.py', 'raw.py', 'scraper.py']
    errors = []

    # Running scripts sequentially
    for script in scripts:
        error = run_script(script)
        if error:
            errors.append((script, error))
        gc.collect()  # Giải phóng bộ nhớ không cần thiết
        logging.info("Memory cleaned up.")

    if errors:
        logging.error(f"Errors occurred in scripts: {errors}")
        exit(1)


if __name__ == '__main__':
    main()
