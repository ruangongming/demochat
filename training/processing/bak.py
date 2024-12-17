# import os
# import shutil
# import logging
# from config import CODE_DIRECTORIES, BACKUP_DIR, SOURCE_EXTENSIONS
#
# # Cấu hình logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#
#
# def backup_code_files():
#     """Sao lưu các tệp mã nguồn và đổi đuôi thành .bak"""
#     for directory in CODE_DIRECTORIES:
#         for root, _, files in os.walk(directory):
#             for file in files:
#                 # Chỉ sao lưu các file mã nguồn có đuôi phù hợp
#                 if any(file.endswith(ext) for ext in SOURCE_EXTENSIONS):
#                     file_path = os.path.join(root, file)
#
#                     # Đường dẫn tới tệp sao lưu với đuôi .bak
#                     relative_path = os.path.relpath(file_path, directory)
#                     backup_file_path = os.path.join(BACKUP_DIR, relative_path + '.bak')
#
#                     # Tạo thư mục đích nếu cần
#                     os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
#
#                     # Sao chép tệp và đổi đuôi thành .bak
#                     shutil.copy(file_path, backup_file_path)
#                     logging.info(f"Đã sao lưu {file_path} tới {backup_file_path}")
#
#
# if __name__ == "__main__":
#     backup_code_files()
