import time
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from selenium import webdriver

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

class DirectLinkApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DirectLink Auto Bot")
        self.root.geometry("650x380")
        
        self.is_running = False
        self.thread = None
        self.loop_count = 0

        # --- UI Setup ---
        pad_x = 10
        pad_y = 5

        # Wi-Fi Profile
        tk.Label(root, text="Tên Wi-Fi (SSID):", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", padx=pad_x, pady=pad_y)
        self.wifi_entry = tk.Entry(root, width=50, font=("Arial", 10))
        self.wifi_entry.grid(row=0, column=1, padx=pad_x, pady=pad_y)
        current_wifi = get_current_wifi_profile()
        if current_wifi:
            self.wifi_entry.insert(0, current_wifi)

        # Target URL
        tk.Label(root, text="URL cần chạy:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", padx=pad_x, pady=pad_y)
        self.url_entry = tk.Entry(root, width=50, font=("Arial", 10))
        self.url_entry.grid(row=1, column=1, padx=pad_x, pady=pad_y)
        self.url_entry.insert(0, "https://cryptolinkforearn.com/dl/eSYY2EjO")

        # Options
        opt_frame = tk.Frame(root)
        opt_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=pad_x, pady=pad_y)
        
        tk.Label(opt_frame, text="Tự nghỉ sau:", font=("Arial", 10)).pack(side="left", padx=(10, 2))
        self.loop_threshold_var = tk.StringVar(value="Không nghỉ")
        ttk.Combobox(opt_frame, textvariable=self.loop_threshold_var, values=["Không nghỉ", "50", "100", "150", "200"], width=10, state="readonly").pack(side="left")

        tk.Label(opt_frame, text="vòng, nghỉ", font=("Arial", 10)).pack(side="left", padx=2)
        self.rest_duration_var = tk.StringVar(value="60")
        ttk.Combobox(opt_frame, textvariable=self.rest_duration_var, values=["30", "60", "90", "120"], width=4, state="readonly").pack(side="left")
        tk.Label(opt_frame, text="s", font=("Arial", 10)).pack(side="left")

        # Thêm Checkbox cấu hình chạy ngầm
        self.headless_var = tk.BooleanVar(value=True)
        tk.Checkbutton(opt_frame, text="Chạy ngầm (Ẩn Chrome)", variable=self.headless_var, font=("Arial", 10), state="normal").pack(side="left", padx=(15, 0))

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        self.start_btn = tk.Button(btn_frame, text="▶ Bắt đầu", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=15, command=self.start_bot)
        self.start_btn.pack(side="left", padx=10)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹ Dừng lại", bg="#F44336", fg="white", font=("Arial", 10, "bold"), width=15, state="disabled", command=self.stop_bot)
        self.stop_btn.pack(side="left", padx=10)

        # Trạng thái đếm ngược thời gian nghỉ
        stats_frame = tk.Frame(root)
        stats_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=pad_x, pady=(10, 0))
        
        self.countdown_label = tk.Label(stats_frame, text="", font=("Arial", 10, "bold"), fg="#FF5722")
        self.countdown_label.pack(side="left", padx=20)

        # Giao diện Nhật ký (Log tối giản)
        log_frame = tk.Frame(root)
        log_frame.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=pad_x, pady=pad_y)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, width=70, height=8, font=("Arial", 9), state="disabled", bg="#f9f9f9")
        self.log_area.pack(fill="both", expand=True)
        
        root.grid_rowconfigure(5, weight=1)

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

    def reconnect_wifi_windows(self, ssid):
        self.log(f"Đang làm mới Wi-Fi: {ssid}...")
        subprocess.run(['netsh', 'wlan', 'disconnect'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(0.05) # Vừa ngắt mạng xong là kết nối lại luôn
        
        result = subprocess.run(['netsh', 'wlan', 'connect', f'name={ssid}'], capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW)
        output = result.stdout.strip()
        
        if result.returncode == 0 and ("successfully" in output.lower() or "thành công" in output.lower() or "hoàn tất" in output.lower()):
            pass # Thành công, không cần log dồn dập
        else:
            subprocess.run(['netsh', 'wlan', 'connect', f'ssid={ssid}', f'name={ssid}'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
        if self.wait_for_internet():
            self.log("✓ Internet đã sẵn sàng.")
            time.sleep(1.5) # Giữ đúng thời gian chờ 1.5s theo ý bạn
        else:
            self.log("⚠ Không thể kết nối Internet!")

    def wait_for_internet(self, timeout=15):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running:
                break
            try:
                # Giảm timeout từ 1s xuống 0.3s để phát hiện mạng lặp nhanh hơn, tránh treo 1s mỗi lần rớt
                socket.create_connection(("8.8.8.8", 53), timeout=0.3)
                return True
            except OSError:
                time.sleep(0.05) # Tăng tốc x2
        return False

    def start_bot(self):
        wifi = self.wifi_entry.get().strip()
        url = self.url_entry.get().strip()
        
        if not wifi or not url:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đủ Tên Wi-Fi và URL!")
            return

        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.loop_count = 0
        self.countdown_label.config(text="")
        self.log("▶ Bắt đầu chạy Bot...")

        is_headless = self.headless_var.get()
        # Khởi chạy trong Thread riêng để không block giao diện
        self.thread = threading.Thread(target=self.bot_task, args=(wifi, url, is_headless), daemon=True)
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

    def bot_task(self, wifi, url, is_headless):
        threshold_val = self.loop_threshold_var.get()
        rest_val = self.rest_duration_var.get()
        threshold = int(threshold_val) if threshold_val.isdigit() else 0
        rest_duration = int(rest_val) if rest_val.isdigit() else 60

        options = webdriver.ChromeOptions()
        options.add_argument("--incognito")
        options.page_load_strategy = 'none' # KHÔNG CHỜ: Bắn lệnh tải URL xong lập tức sang bước tiếp theo
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--mute-audio")
        options.add_argument("--disable-web-security") # Bỏ qua check bảo mật chéo trang (nhanh hơn)
        options.add_argument("--blink-settings=imagesEnabled=false") # Ép tắt tải ảnh triệt để từ core
        options.add_argument("--window-size=1920,1080") # Thêm kích thước ảo để chống crash ở chế độ ẩn
        options.add_argument("--remote-allow-origins=*") # Sửa lỗi Websocket/Origin
        options.add_argument("--ignore-certificate-errors") # Bỏ qua lỗi chứng chỉ
        
        if is_headless:
            options.add_argument("--headless=new")

        # Chặn tải Hình ảnh, CSS và Fonts để tiết kiệm băng thông và tăng tốc
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2
        }
        options.add_experimental_option("prefs", prefs)

        driver = None
        
        try:
            driver = webdriver.Chrome(options=options)
            try:
                driver.delete_all_cookies()
            except Exception:
                pass
                
            self.log(f"Đang chạy URL (Vòng {self.loop_count + 1})...")
            self.load_url(driver, url)

            while self.is_running:
                self.loop_count += 1
                
                if threshold > 0 and self.loop_count > 0 and self.loop_count % threshold == 0:
                    self.clear_log()
                    self.log(f"Đạt mốc {threshold} vòng. Bắt đầu dọn dẹp và nghỉ ngơi {rest_duration}s...")
                    
                    subprocess.run(['netsh', 'wlan', 'disconnect'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    try:
                        if len(driver.window_handles) > 1:
                            main_window = driver.window_handles[0]
                            for handle in driver.window_handles[1:]:
                                driver.switch_to.window(handle)
                                driver.close()
                            driver.switch_to.window(main_window)
                    except Exception:
                        pass

                    try:
                        driver.delete_all_cookies()
                    except Exception:
                        pass
                        
                    for i in range(rest_duration, 0, -1):
                        if not self.is_running: break
                        self.root.after(0, lambda sec=i: self.countdown_label.config(text=f"Nghỉ: {sec}s"))
                        time.sleep(1)
                    self.root.after(0, lambda: self.countdown_label.config(text=""))
                    
                    if self.is_running:
                        self.log("Tiếp tục chạy...")
                        self.reconnect_wifi_windows(wifi)
                        
                        self.log(f"Đang chạy URL (Vòng {self.loop_count + 1})...")
                        self.load_url(driver, url)
                else:
                    self.fast_reconnect_and_load(driver, wifi, url)
                    
        except Exception as e:
            self.log(f"Lỗi: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        self.is_running = False
        self.root.after(0, lambda: self.set_buttons_state(False))

    def load_url(self, driver, url):
        while self.is_running:
            try:
                driver.get(url)
                timeout = 10
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
                    self.log("✓ JS đã chạy xong (Không thấy URL thay đổi, có thể đã tính view).")
                
                break
            except Exception:
                if not self.is_running: break
                time.sleep(0.1)

    def fast_reconnect_and_load(self, driver, ssid, url):
        self.log(f"Đang làm mới Wi-Fi: {ssid}...")
        
        subprocess.run(['netsh', 'wlan', 'disconnect'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(0.05) # Cực hạn: ngắt xong nối lại gần như ngay lập tức

        result = subprocess.run(['netsh', 'wlan', 'connect', f'name={ssid}'], capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW)
        output = result.stdout.strip()
        
        if result.returncode == 0 and ("successfully" in output.lower() or "thành công" in output.lower() or "hoàn tất" in output.lower()):
            pass
        else:
            subprocess.run(['netsh', 'wlan', 'connect', f'ssid={ssid}', f'name={ssid}'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

        if self.wait_for_internet():
            self.log("✓ Internet đã sẵn sàng.")
            time.sleep(1.5) # Giữ đúng thời gian chờ 1.5s theo ý bạn
        else:
            self.log("⚠ Không thể kết nối Internet!")

        self.log(f"Đang chạy URL (Vòng {self.loop_count + 1})...")
        self.load_url(driver, url)

if __name__ == "__main__":
    root = tk.Tk()
    app = DirectLinkApp(root)
    root.mainloop()