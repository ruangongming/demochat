# File mutilrun.py

import asyncio
import logging
import sys
import os
import gc
from logger import get_logger  # Import get_logger từ logger.py
from config import config

logger = get_logger(__name__, level=logging.INFO)  # Đặt mức độ log là INFO cho mutilrun.py

# Danh sách các script cần chạy
scripts = ['db.py', 'raw.py', 'scraper.py']  # Thay đổi danh sách này theo nhu cầu của bạn

async def run_script(script_name: str) -> None:
    """Chạy một script và ghi lại kết quả."""
    logger.info(f"Running {script_name}...")
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, script_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode == 0:
            logger.info(f"Finished running {script_name}.")
        else:
            logger.error(f"Script {script_name} exited with return code {process.returncode}.")
            logger.error(f"Error output: {stderr.decode().strip()}")
    except Exception as e:
        logger.error(f"Failed to run {script_name}. Error: {e}")

    gc.collect()  # Giải phóng bộ nhớ không cần thiết
    # logger.debug("Memory cleaned up.")

async def main():
    """Chạy tất cả các script trong danh sách tuần tự."""
    for script in scripts:
        await run_script(script)

if __name__ == '__main__':
    asyncio.run(main())
