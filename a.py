from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from time import sleep

# Đường dẫn tới file chứa danh sách số điện thoại
phone_numbers_file = "expanded_phone_numbers.txt"

# Đường dẫn tới ChromeDriver và Brave Browser
brave_path = "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe"

# Cấu hình ChromeOptions để dùng Brave
chrome_options = Options()
chrome_options.binary_location = brave_path

# Khởi tạo WebDriver với Brave và chỉ mở một phiên duy nhất
driver = webdriver.Chrome(service=Service(brave_path), options=chrome_options)

# Hàm tìm kiếm số điện thoại trên Zalo
def search_on_zalo(phone_number):
    driver.get("https://chat.zalo.me/")
    sleep(5)  # Đợi trang tải

    # Tìm hộp tìm kiếm và nhập số điện thoại
    try:
        search_box = driver.find_element("css selector", "input[placeholder='Tìm kiếm']")
        search_box.clear()
        search_box.send_keys(phone_number)
        sleep(3)  # Đợi kết quả
    except Exception as e:
        print(f"Lỗi khi tìm kiếm số {phone_number}: {e}")

# Đọc danh sách số điện thoại từ file
with open(phone_numbers_file, "r") as file:
    phone_numbers = file.readlines()

# Tìm kiếm từng số điện thoại trong một phiên duy nhất
for phone_number in phone_numbers:
    search_on_zalo(phone_number.strip())

# Đóng trình duyệt sau khi hoàn tất
driver.quit()
