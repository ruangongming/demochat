# logger.py
import logging
import sys
from config import config

def get_logger(name: str, level: int = logging.WARNING) -> logging.Logger:
    """Tạo và cấu hình logger với tên cụ thể và mức độ log tùy chỉnh."""
    logger = logging.getLogger(name)
    logger.setLevel(level)  # Đặt mức độ log tùy chỉnh

    # Kiểm tra xem logger đã được cấu hình handler hay chưa
    if not logger.handlers:
        # Tạo formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Tạo file handler để ghi log vào file
        file_handler = logging.FileHandler(config.log_path, encoding='utf-8')
        file_handler.setFormatter(formatter)

        # Tạo console handler để hiển thị log trên console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        # Thêm các handler vào logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        # Ngăn chặn log bị ghi nhiều lần
        logger.propagate = False

    return logger
