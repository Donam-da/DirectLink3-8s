import time
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import selenium.webdriver.chrome.webdriver
import selenium.webdriver.chrome.service
import json
import base64
import hashlib
import hmac
import datetime
import os
import sys
import ctypes

# BẠN HÃY THAY ĐỔI CHUỖI NÀY THÀNH MỘT MẬT KHẨU BÍ MẬT CỦA RIÊNG BẠN
SECRET_KEY = b"THAY_DOI_CHUOI_NAY_THANH_MAT_KHAU_CUA_BAN"

def get_current_wifi_profile():
    """Tự động lấy tên Profile Wi-Fi đang kết nối hiện tại"""
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW)
        lines = result.stdout.splitlines()
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith("Profile") or line_strip.startswith("Hồ sơ"):
                return line.split(":", 1)[1].strip()
        for line in lines:
            line_strip = line.strip()
            if line_strip.startswith("SSID") and not line_strip.startswith("BSSID"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""

def auto_detect_network():
    """Tự động phát hiện Card mạng đang dùng Internet (hỗ trợ nhận diện USB Wi-Fi)"""
    try:
        ps_command = """
        $routes = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue
        if ($routes) {
            $activeIfIndex = $routes[0].InterfaceIndex
            $adapter = Get-NetAdapter -InterfaceIndex $activeIfIndex -ErrorAction SilentlyContinue
            if ($adapter) {
                $isUSB = ($adapter.InterfaceDescription -match 'USB') -or ($adapter.PnPDeviceID -match '^USB')
                $media = $adapter.MediaType
                $name = $adapter.Name
                Write-Output "$name|$media|$isUSB"
            }
        }
        """
        result = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        output = result.stdout.strip()
        if output:
            parts = output.split('|')
            if len(parts) >= 3:
                name = parts[0]
                media = parts[1]
                is_usb = parts[2].strip().lower() == 'true'
                
                # Nếu là mạng không dây (Wi-Fi)
                if '802.11' in media or 'Wi-Fi' in name or 'Wireless' in name:
                    if is_usb:
                        # Là USB Wi-Fi -> Chuyển sang kịch bản Ethernet, lấy tên Card mạng vật lý
                        return "Ethernet", name
                    else:
                        # Là Laptop Wi-Fi -> Kịch bản Wi-Fi, lấy tên Profile (SSID)
                        ssid = get_current_wifi_profile()
                        return "Wi-Fi", ssid if ssid else name
                else:
                    # Là mạng dây cắm cáp quang bình thường
                    return "Ethernet", name
    except Exception:
        pass
    
    # Fallback dự phòng nếu PowerShell lỗi
    ssid = get_current_wifi_profile()
    if ssid:
        return "Wi-Fi", ssid
    return "Wi-Fi", "Wi-Fi"

def get_hwid():
    """Lấy mã định danh phần cứng (UUID) của máy Windows"""
    try:
        hwid = subprocess.check_output('wmic csproduct get uuid', creationflags=subprocess.CREATE_NO_WINDOW).decode().split('\n')[1].strip()
        return hwid
    except Exception:
        return "UNKNOWN_HWID"

def validate_key(key, hwid):
    """Giải mã và kiểm tra tính hợp lệ của Key"""
    try:
        payload = json.loads(base64.b64decode(key).decode('utf-8'))
        data_str = payload['data']
        sig = payload['sig']
        
        expected_sig = hmac.new(SECRET_KEY, data_str.encode('utf-8'), hashlib.sha256).hexdigest()
        if expected_sig != sig:
            return False, "Key không hợp lệ hoặc đã bị thay đổi!"
            
        data = json.loads(data_str)
        if data['hwid'] != hwid:
            return False, "Key này không dành cho máy này (Sai mã HWID)!"
            
        exp_date = datetime.datetime.strptime(data['exp'], "%Y-%m-%d %H:%M")
        if datetime.datetime.now() > exp_date:
            return False, "Key đã hết hạn sử dụng!"
            
        return True, exp_date
    except Exception:
        return False, "Key sai định dạng!"

class AuthWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("Kích hoạt bản quyền")
        self.root.geometry("450x250")
        
        self.hwid = get_hwid()
        
        tk.Label(root, text="Mã máy (HWID) của bạn:", font=("Arial", 10, "bold")).pack(pady=(20, 5))
        
        hwid_frame = tk.Frame(root)
        hwid_frame.pack()
        self.hwid_entry = tk.Entry(hwid_frame, width=40, font=("Arial", 10))
        self.hwid_entry.insert(0, self.hwid)
        self.hwid_entry.configure(state='readonly')
        self.hwid_entry.pack(side="left", padx=5)
        
        tk.Button(hwid_frame, text="Copy", command=lambda: (self.root.clipboard_clear(), self.root.clipboard_append(self.hwid))).pack(side="left")
        
        tk.Label(root, text="Nhập Key kích hoạt:", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        self.key_entry = tk.Entry(root, width=50, font=("Arial", 10))
        self.key_entry.pack(pady=5)
        
        tk.Button(root, text="Kích Hoạt", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), command=self.check_activation).pack(pady=15)

        self.key_file = "license.key"
        if os.path.exists(self.key_file):
            with open(self.key_file, "r", encoding="utf-8") as f:
                key = f.read().strip()
                is_valid, result = validate_key(key, self.hwid)
                if is_valid:
                    self.on_success(result) # Key ok, tự động vào app, truyền thời gian hết hạn vào
                else:
                    self.key_entry.insert(0, key) # Sai hoặc hết hạn, hiện lại key cũ lên

    def check_activation(self):
        key = self.key_entry.get().strip()
        is_valid, result = validate_key(key, self.hwid)
        if is_valid:
            with open(self.key_file, "w", encoding="utf-8") as f:
                f.write(key)
            self.on_success(result)
        else:
            messagebox.showerror("Lỗi Kích Hoạt", result)

class DirectLinkApp:
    def __init__(self, root, exp_date):
        self.root = root
        self.exp_date = exp_date
        self.root.title("DirectLink Auto Bot")
        self.root.geometry("650x380")
        
        self.is_running = False
        self.thread = None
        self.loop_count = 0
        self.config_file = "config.json"

        # --- UI Setup ---
        pad_x = 10
        pad_y = 5

        # Network Profile
        tk.Label(root, text="Loại mạng:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=pad_x, pady=pad_y)
        
        net_frame = tk.Frame(root)
        net_frame.grid(row=0, column=1, sticky="w", padx=pad_x, pady=pad_y)
        
        self.net_type_var = tk.StringVar(value="Đang quét...")
        self.net_type_cb = ttk.Combobox(net_frame, textvariable=self.net_type_var, values=["Wi-Fi", "Ethernet"], width=12, state="disabled")
        self.net_type_cb.pack(side="left")
        
        tk.Label(net_frame, text=" Tên:", font=("Arial", 10)).pack(side="left")
        self.wifi_entry = tk.Entry(net_frame, width=28, font=("Arial", 10))
        self.wifi_entry.pack(side="left", padx=5)
        
        self.wifi_entry.insert(0, "Đang nhận diện...")
        self.wifi_entry.config(state="disabled")
            
        self.net_type_cb.bind("<<ComboboxSelected>>", self.on_net_type_change)

        # Target URL
        tk.Label(root, text="URL cần chạy:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=pad_x, pady=pad_y)
        self.url_entry = tk.Entry(root, width=50, font=("Arial", 10))
        self.url_entry.grid(row=1, column=1, padx=pad_x, pady=pad_y)
        
        saved_url = self.load_saved_url()
        if saved_url:
            self.url_entry.insert(0, saved_url)

        # Options
        opt_frame = tk.Frame(root)
        opt_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=pad_x, pady=pad_y)
        
        tk.Label(opt_frame, text="Số vòng lặp:", font=("Arial", 10)).pack(side="left", padx=(10, 2))
        # Người dùng có thể chọn mốc hoặc tự gõ vào số vòng lặp mong muốn
        self.total_loops_var = tk.StringVar(value="Không giới hạn")
        ttk.Combobox(opt_frame, textvariable=self.total_loops_var, values=["Không giới hạn", "50", "100", "200", "500", "1000"], width=15, state="normal").pack(side="left")

        # Thêm Checkbox cấu hình chạy ngầm
        self.headless_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opt_frame, text="Chạy ngầm (Ẩn Chrome)", variable=self.headless_var, font=("Arial", 10), state="normal").pack(side="left", padx=(15, 0))

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        self.start_btn = tk.Button(btn_frame, text="▶ Bắt đầu", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=15, state="disabled", command=self.start_bot)
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹ Dừng lại", bg="#F44336", fg="white", font=("Arial", 10, "bold"), width=15, state="disabled", command=self.stop_bot)
        self.stop_btn.pack(side="left", padx=10)

        # Trạng thái đếm ngược thời gian nghỉ
        stats_frame = tk.Frame(root)
        stats_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=pad_x, pady=(10, 0))
        
        self.countdown_label = tk.Label(stats_frame, text="", font=("Arial", 10, "bold"), fg="#FF5722")
        self.countdown_label.pack(side="left", padx=20)

        # Nhãn hiển thị thời gian sống của Key
        self.expiry_label = tk.Label(stats_frame, text="", font=("Arial", 9, "italic"), fg="#757575")
        self.expiry_label.pack(side="right", padx=20)

        # Giao diện Nhật ký (Log tối giản)
        log_frame = tk.Frame(root)
        log_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=pad_x, pady=pad_y)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, width=70, height=8, font=("Arial", 9), state="disabled", bg="#f9f9f9")
        self.log_area.pack(fill="both", expand=True)
        
        root.grid_rowconfigure(5, weight=1)

        # Bắt đầu kiểm tra hạn sử dụng định kỳ ngay cả khi không chạy bot
        self.check_expiry_periodic()
        
        # Bắt đầu quét mạng ngầm
        self.log("Đang nhận diện cấu hình mạng tự động, vui lòng đợi vài giây...")
        threading.Thread(target=self.detect_network_async, daemon=True).start()
        
    def detect_network_async(self):
        detected_type, detected_name = auto_detect_network()
        self.root.after(0, self.on_network_detected, detected_type, detected_name)

    def on_network_detected(self, detected_type, detected_name):
        self.net_type_cb.config(state="readonly")
        self.wifi_entry.config(state="normal")
        self.start_btn.config(state="normal")
        
        self.net_type_var.set(detected_type)
        self.wifi_entry.delete(0, tk.END)
        self.wifi_entry.insert(0, detected_name)
        self.log(f"✓ Đã tự động nhận diện thành công: {detected_type} - {detected_name}")
        
    def on_net_type_change(self, event=None):
        self.wifi_entry.delete(0, tk.END)
        if self.net_type_var.get() == "Ethernet":
            try:
                ps_command = "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | Select-Object -First 1 -ExpandProperty Name"
                result = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                name = result.stdout.strip()
                self.wifi_entry.insert(0, name if name else "Ethernet")
            except:
                self.wifi_entry.insert(0, "Ethernet")
        else:
            ssid = get_current_wifi_profile()
            self.wifi_entry.insert(0, ssid if ssid else "Wi-Fi")

    def load_saved_url(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    return config.get("url", "")
            except Exception:
                pass
        return ""

    def save_url(self, url):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump({"url": url}, f)
        except Exception:
            pass

    def check_expiry_periodic(self):
        now = datetime.datetime.now()
        if now > self.exp_date:
            self.is_running = False # Tự động dừng Bot ngầm nếu có
            messagebox.showwarning("Hết hạn", "Key kích hoạt của bạn đã hết thời gian sử dụng!\nPhần mềm sẽ tự động thoát.")
            os._exit(0)
            
        # Tính toán và hiển thị thời gian còn lại
        remaining = self.exp_date - now
        days = remaining.days
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            time_str = f"{days} ngày {hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
        self.expiry_label.config(text=f"Bản quyền còn: {time_str}")
        
        self.root.after(1000, self.check_expiry_periodic) # Kiểm tra lại sau mỗi 1 giây

    def log(self, message):
        """Ghi log ngắn gọn, tối giản an toàn cho luồng phụ (thread-safe)"""
        def append_log():
            self.log_area.config(state="normal")
            current_time = time.strftime("%H:%M:%S")
            self.log_area.insert(tk.END, f"[{current_time}] {message}\n")
            self.log_area.see(tk.END)
            self.log_area.config(state="disabled")
        self.root.after(0, append_log)

    def clear_log(self):
        """Xóa log an toàn cho luồng phụ (thread-safe)"""
        def _clear():
            self.log_area.config(state="normal")
            self.log_area.delete('1.0', tk.END)
            self.log_area.config(state="disabled")
        self.root.after(0, _clear)

    def check_ipv6(self):
        """Kiểm tra xem máy đã nhận được kết nối IPv6 thực tế ra internet chưa"""
        try:
            # Dùng DNS IPv6 của Google để test nhanh
            sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            sock.connect(("2001:4860:4860::8888", 53))
            sock.close()
            return True
        except OSError:
            return False

    def setup_driver(self, is_headless):
        """Tách hàm khởi tạo Driver để dễ dàng Refresh Chrome sau mỗi 200 vòng"""
        options = Options()
        options.add_argument("--incognito")
        options.page_load_strategy = 'none' # Bắn lệnh tải URL xong lập tức sang bước tiếp theo
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--mute-audio")
        options.add_argument("--disable-web-security")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--ignore-certificate-errors")
        
        if is_headless:
            options.add_argument("--headless=new")

        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2
        }
        options.add_experimental_option("prefs", prefs)

        driver = webdriver.Chrome(options=options)
        try: driver.delete_all_cookies()
        except Exception: pass
        return driver

    def clean_tabs_and_cookies(self, driver):
        try:
            if len(driver.window_handles) > 1:
                main_window = driver.window_handles[0]
                for handle in driver.window_handles[1:]:
                    driver.switch_to.window(handle)
                    driver.close()
                driver.switch_to.window(main_window)
        except Exception: pass
        try: driver.delete_all_cookies()
        except Exception: pass

    def wait_for_internet(self, timeout=5):
        start_time = time.time()
        has_ipv4 = False
        while time.time() - start_time < timeout:
            if not self.is_running:
                break
            try:
                if not has_ipv4:
                    socket.create_connection(("8.8.8.8", 53), timeout=0.3)
                    has_ipv4 = True
                
                # Khi đã có IPv4, tiếp tục chờ hệ thống cấp phát xong IPv6
                if has_ipv4:
                    if self.check_ipv6():
                        return True
            except OSError:
                pass
            time.sleep(0.2) # Chờ một khoảng ngắn, không spam request quá nhanh
        return False

    def start_bot(self):
        wifi = self.wifi_entry.get().strip()
        url = self.url_entry.get().strip()
        net_type = self.net_type_var.get()
        
        if not wifi or not url:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đủ Tên mạng và URL!")
            return
            
        self.save_url(url)

        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.loop_count = 0
        self.countdown_label.config(text="")
        self.log("▶ Bắt đầu chạy Bot...")
        if net_type == "Ethernet":
            self.log("Lưu ý: Công cụ phải được chạy bằng quyền Administrator để đổi MAC!")

        is_headless = self.headless_var.get()
        # Khởi chạy trong Thread riêng để không block giao diện
        self.thread = threading.Thread(target=self.bot_task, args=(wifi, url, is_headless, net_type), daemon=True)
        self.thread.start()

    def stop_bot(self):
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.log("⏹ Đã dừng Bot.")

    def set_buttons_state(self, is_running):
        state = "normal" if not is_running else "disabled"
        self.start_btn.config(state=state)
        self.stop_btn.config(state="disabled" if not is_running else "normal")

    def prepare_next_mac(self, network_name):
        self.log("Đang nạp sẵn MAC mới cho vòng tiếp theo...")
        ps_command = f'$randomMAC = ("02" + ((1..5) | ForEach-Object {{ "{{0:X2}}" -f (Get-Random -Min 0 -Max 256) }}) -join "").Replace(" ",""); Set-NetAdapterAdvancedProperty -Name "{network_name}" -RegistryKeyword "NetworkAddress" -RegistryValue $randomMAC -NoRestart; Write-Output $randomMAC'
        result = subprocess.run(["powershell", "-Command", ps_command], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        new_mac = result.stdout.strip()
        if new_mac:
            formatted_mac = ":".join([new_mac[i:i+2] for i in range(0, len(new_mac), 2)])
            self.log(f"Đã nạp sẵn MAC: {formatted_mac} (Sẽ áp dụng khi reset mạng)")
        elif result.stderr:
            self.log("⚠ Lỗi: Card không hỗ trợ đổi MAC hoặc sai Tên mạng!")
        else:
            self.log("Đã nạp sẵn MAC cho vòng sau")

    def bot_task(self, wifi, url, is_headless, net_type):
        total_loops_str = self.total_loops_var.get()
        total_loops = -1
        if total_loops_str.isdigit():
            total_loops = int(total_loops_str)

        driver = None
        
        try:
            if net_type == "Ethernet":
                self.log(f"Đang nạp MAC khởi động cho vòng 1 ({net_type})...")
                self.prepare_next_mac(wifi)

            # Khởi tạo Chrome cho cả Wi-Fi và Ethernet
            driver = self.setup_driver(is_headless)

            while self.is_running:
                # Kiểm tra hạn sử dụng liên tục trong lúc chạy
                if datetime.datetime.now() > self.exp_date:
                    self.log("⚠ KEY ĐÃ HẾT HẠN! Đang tắt phần mềm...")
                    break

                if total_loops > 0 and self.loop_count >= total_loops:
                    self.log("✓ Đã hoàn thành số lượng vòng lặp yêu cầu!")
                    break

                self.loop_count += 1
                
                # Đảo quy trình: Đổi IP TRƯỚC khi chạy URL để đảm bảo View 1 cũng được làm mới mạng
                if self.loop_count > 1 and (self.loop_count - 1) % 200 == 0:
                    self.clear_log()
                    self.log(f"Đã chạy xong {self.loop_count - 1} vòng. Đóng trình duyệt, xóa dữ liệu, thêm 1 lần đổi MAC & reset mạng, nghỉ 30s...")
                    if driver:
                        try: driver.quit()
                        except: pass
                    network_ok = self.perform_double_network_reset(wifi, net_type)
                    self.rest_countdown(30)
                    driver = self.setup_driver(is_headless)
                elif self.loop_count > 1 and (self.loop_count - 1) % 25 == 0:
                    self.clear_log()
                    self.log(f"Đã chạy xong {self.loop_count - 1} vòng. Thực hiện thêm 1 lần đổi MAC & reset mạng...")
                    network_ok = self.perform_double_network_reset(wifi, net_type)
                else:
                    network_ok = self.fast_reconnect(wifi, net_type)
                    
                if not self.is_running: break

                # Nếu quá 5s mạng lỗi/không có IPv6 thì lập tức nhảy sang làm mới vòng lặp khác, KHÔNG tải URL
                if not network_ok:
                    self.log("⚠ Mạng lỗi/thiếu IPv6. Bỏ qua view này và thử lại ở vòng mới ngay...")
                    continue

                if net_type == "Ethernet":
                    self.prepare_next_mac(wifi)

                self.clean_tabs_and_cookies(driver) # Xóa bộ nhớ tạm của Chrome trước mỗi view
                self.log(f"Đang chạy URL (Vòng {self.loop_count})...")
                self.load_url(driver, url)
                    
        except Exception as e:
            self.log(f"Lỗi: {e}")
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass

        self.is_running = False
        self.root.after(0, lambda: self.set_buttons_state(False))

    def perform_double_network_reset(self, network_name, net_type):
        """Thực hiện nhồi reset mạng 2 lần liên tiếp để lấy IP thực sự mới"""
        success = False
        for i in range(2):
            if not self.is_running: break
            self.log(f"Tiến hành Reset {net_type} lần {i + 1}/2...")
            
            if net_type == "Wi-Fi":
                subprocess.run(['netsh', 'wlan', 'disconnect'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(1.0)
                
                result = subprocess.run(['netsh', 'wlan', 'connect', f'name={network_name}'], capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW)
                output = result.stdout.strip()
                if result.returncode != 0 or ("successfully" not in output.lower() and "thành công" not in output.lower() and "hoàn tất" not in output.lower()):
                    subprocess.run(['netsh', 'wlan', 'connect', f'ssid={network_name}', f'name={network_name}'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                self.prepare_next_mac(network_name) # Đổi MAC mới cho lần reset này
                
                # Lệnh thao tác mềm siêu nhẹ (Không tắt card mạng)
                if "Wi-Fi" in network_name or "Wireless" in network_name:
                    subprocess.run(['netsh', 'wlan', 'disconnect'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    time.sleep(0.5)
                    if hasattr(self, 'cached_ssid') and self.cached_ssid:
                        subprocess.Popen(['netsh', 'wlan', 'connect', f'name={self.cached_ssid}'], creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.run(['ipconfig', '/release'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    subprocess.run(['ipconfig', '/renew'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    
                time.sleep(1.0)
            
            if self.wait_for_internet(timeout=10 if net_type == "Ethernet" else 5):
                self.log(f"✓ {net_type} (kèm IPv6) đã sẵn sàng (Lần {i + 1}/2).")
                success = True
            else:
                self.log(f"⚠ Mạng chưa ổn định (Lần {i + 1}/2).")
                success = False
            
            if i == 0: # Chỉ chờ một chút ở lần trung gian giữa 2 lần reset
                time.sleep(2.0 if net_type == "Ethernet" else 1.0)
        return success

    def rest_countdown(self, seconds):
        self.log(f"Bắt đầu nghỉ {seconds}s...")
        for i in range(seconds, 0, -1):
            if not self.is_running: break
            self.root.after(0, lambda sec=i: self.countdown_label.config(text=f"Nghỉ: {sec}s"))
            time.sleep(1)
        self.root.after(0, lambda: self.countdown_label.config(text=""))

    def fast_reconnect(self, network_name, net_type):
        self.log(f"Đang làm mới {net_type}: {network_name}...")
        
        if net_type == "Wi-Fi":
            subprocess.run(['netsh', 'wlan', 'disconnect'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(0.5)
            subprocess.Popen(['netsh', 'wlan', 'connect', f'name={network_name}'], creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            # Lệnh thao tác mềm siêu nhẹ (Không tắt card mạng)
            if "Wi-Fi" in network_name or "Wireless" in network_name:
                subprocess.run(['netsh', 'wlan', 'disconnect', f'interface={network_name}'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                time.sleep(0.5)
                if hasattr(self, 'cached_ssid') and self.cached_ssid:
                    subprocess.Popen(['netsh', 'wlan', 'connect', f'name={self.cached_ssid}', f'interface={network_name}'], creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.run(['ipconfig', '/release'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run(['ipconfig', '/renew'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

            # Chạy ngầm nạp sẵn MAC cho vòng tiếp theo ngay trong lúc chờ mạng kết nối
            threading.Thread(target=self.prepare_next_mac, args=(network_name,), daemon=True).start()

        if self.wait_for_internet(timeout=10 if net_type == "Ethernet" else 5):
            self.log("✓ Internet (kèm IPv6) đã sẵn sàng.")
            time.sleep(1.0) 
            return True
        else:
            self.log("⚠ Không thể kết nối hoặc thiếu IPv6!")
            return False

    def load_url(self, driver, url):
        while self.is_running:
            try:
                driver.get(url)
                timeout = 5
                start_time = time.time()
                redirected = False
                
                while self.is_running and (time.time() - start_time < timeout):
                    try:
                        current_url = driver.current_url
                        if current_url and not current_url.startswith("data:"):
                            if current_url.rstrip("/") != url.rstrip("/"):
                                self.log("✓ JS đã chạy và chuyển hướng thành công!")
                                redirected = True
                                time.sleep(0.05) # Đã nhảy URL tức là web đã gửi lệnh lên server, không cần chờ nữa
                                break
                    except Exception:
                        pass
                    time.sleep(0.05) # Quét URL 20 lần/giây, xé gió bắt khoảnh khắc nhảy link
                    
                if not redirected:
                    self.log("⚠ Quá 5s không chuyển hướng (có thể lỗi mạng), bỏ qua view.")
                
                break
            except Exception:
                if not self.is_running: break
                time.sleep(0.1)

if __name__ == "__main__":
    # Kiểm tra và tự động xin quyền Admin nếu chạy file main.py trực tiếp
    def is_admin():
        try: return ctypes.windll.shell32.IsUserAnAdmin()
        except: return False

    if not is_admin():
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        if getattr(sys, 'frozen', False):
            # Dành cho khi đã build thành file .exe
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        else:
            # Dành cho khi chạy bằng file mã nguồn .py
            script = os.path.abspath(sys.argv[0])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        sys.exit()

    root = tk.Tk()
    
    def start_main_app(exp_date):
        for widget in root.winfo_children():
            widget.destroy()
        app = DirectLinkApp(root, exp_date)
        
    # Bật lại cửa sổ yêu cầu Key bản quyền
    AuthWindow(root, start_main_app)
    root.mainloop()