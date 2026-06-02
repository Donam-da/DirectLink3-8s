import time
import socket
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
from selenium import webdriver
from selenium.webdriver.common.by import By

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
        self.root.geometry("650x220")
        
        self.is_running = False
        self.thread = None
        self.loop_count = 0
        self.total_loop_time = 0.0

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

        # Target URLs
        tk.Label(root, text="URL cần chạy\n(Duy nhất 1):", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="nw", padx=pad_x, pady=pad_y)
        
        self.url_entries = []
        url_frame = tk.Frame(root)
        url_frame.grid(row=1, column=1, sticky="w", padx=pad_x, pady=pad_y)
        entry = tk.Entry(url_frame, width=50, font=("Arial", 10))
        entry.pack(pady=3)
        self.url_entries.append(entry)
        self.url_entries[0].insert(0, "https://cryptolinkforearn.com/dl/eSYY2EjO")

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

    def log(self, message):
        pass # Loại bỏ hoàn toàn ghi Log để tối ưu hóa RAM

    def clear_log(self):
        pass

    def update_stats_ui(self, count, avg_time):
        pass

    def reconnect_wifi_windows(self, ssid):
        self.log(f"Đang khởi động lại Wi-Fi: '{ssid}'...")
        subprocess.run(['netsh', 'wlan', 'disconnect'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(0.1) # Tăng tốc x2: Giảm thời gian chờ ngắt mạng
        
        result = subprocess.run(['netsh', 'wlan', 'connect', f'name={ssid}'], capture_output=True, text=True, encoding='utf-8', errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW)
        output = result.stdout.strip()
        
        if result.returncode == 0 and ("successfully" in output.lower() or "thành công" in output.lower() or "hoàn tất" in output.lower()):
            pass # Thành công, không cần log dồn dập
        else:
            self.log("Gửi lệnh dự phòng (Kèm SSID)...")
            subprocess.run(['netsh', 'wlan', 'connect', f'ssid={ssid}', f'name={ssid}'], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
        self.log("Đang chờ mạng kết nối thành công...")
        if self.wait_for_internet():
            self.log("Đã kết nối! Chờ thêm 1.0s cho mạng thật sự ổn định...")
            time.sleep(1.0) # Giảm thời gian chờ ổn định mạng xuống 1s

    def wait_for_internet(self, timeout=15):
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running:
                break
            try:
                socket.create_connection(("8.8.8.8", 53), timeout=1)
                return True
            except OSError:
                time.sleep(0.05) # Tăng tốc x2
        return False

    def start_bot(self):
        wifi = self.wifi_entry.get().strip()
        
        urls = []
        for entry in self.url_entries:
            val = entry.get().strip()
            if val:
                urls.append(val)
        
        if not wifi or not urls:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập đủ Tên Wi-Fi và ít nhất 1 URL!")
            return

        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.log(f"=== BẮT ĐẦU CHẠY TỰ ĐỘNG ({len(urls)} URL) ===")
        self.loop_count = 0
        self.total_loop_time = 0.0
        self.update_stats_ui(0, 0.0)
        self.countdown_label.config(text="")

        # Khởi chạy trong Thread riêng để không block giao diện
        self.thread = threading.Thread(target=self.bot_task, args=(wifi, urls, True), daemon=True) # Mặc định 'True' để luôn chạy ngầm
        self.thread.start()

    def stop_bot(self):
        self.is_running = False
        self.log("=== ĐANG DỪNG... (Sẽ thoát an toàn ở chu kỳ tiếp theo) ===")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def set_buttons_state(self, is_running):
        state = "normal" if not is_running else "disabled"
        self.start_btn.config(state=state)
        self.stop_btn.config(state="disabled" if not is_running else "normal")

    def bot_task(self, wifi, urls, is_headless):
        threshold_val = self.loop_threshold_var.get()
        rest_val = self.rest_duration_var.get()
        threshold = int(threshold_val) if threshold_val.isdigit() else 0
        rest_duration = int(rest_val) if rest_val.isdigit() else 60

        options = webdriver.ChromeOptions()
        options.add_argument("--incognito")
        options.page_load_strategy = 'none' # Không chờ trang load (Tăng tốc web tối đa)
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_argument("--mute-audio")
        
        if is_headless:
            options.add_argument("--headless=new") # Chạy ngầm tiết kiệm RAM

        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        while self.is_running:
            drivers = []
            try:
                self.log(f"Đang khởi động {len(urls)} luồng Chrome...")
                for i in range(len(urls)):
                    if not self.is_running:
                        break
                    drivers.append(webdriver.Chrome(options=options))
                    
                if len(drivers) < len(urls):
                    raise Exception("Bị dừng khi đang khởi động trình duyệt.")
                
                while self.is_running:
                    loop_start_time = time.time()
                    threads = []
                    for i, url in enumerate(urls):
                        if not self.is_running:
                            break
                        t = threading.Thread(target=self.run_single_driver, args=(drivers[i], url))
                        t.start()
                        threads.append(t)
                    
                    # Chờ tất cả các luồng chạy xong vòng lặp hiện tại
                    for t in threads:
                        t.join()
                    
                    if not self.is_running:
                        break

                    if self.is_running:
                        duration = time.time() - loop_start_time
                        self.loop_count += 1
                        self.total_loop_time += duration
                        avg_time = self.total_loop_time / self.loop_count
                        self.root.after(0, lambda c=self.loop_count, a=avg_time: self.update_stats_ui(c, a))
                        
                        if threshold > 0 and self.loop_count > 0 and self.loop_count % threshold == 0:
                            self.log(f"Đã đạt {threshold} vòng. Đóng trình duyệt để giải phóng RAM...")
                            break # Thoát vòng lặp nhỏ để quit driver
                            
                        # NẾU KHÔNG NGHỈ: Reset Wi-Fi bình thường và chạy tiếp
                        self.log("-> Tất cả URL đã hoàn tất! Chuẩn bị Reset Wi-Fi...")
                        self.reconnect_wifi_windows(wifi)
                        
            except Exception as e:
                if self.is_running:
                    self.log(f"Lỗi hệ thống Chrome: {e}")
            finally:
                for d in drivers:
                    try:
                        d.quit()
                    except Exception:
                        pass

            if not self.is_running:
                break
                
            if threshold > 0 and self.loop_count > 0 and self.loop_count % threshold == 0:
                self.log(f"Bắt đầu nghỉ ngơi {rest_duration}s...")
                self.root.after(0, self.clear_log) # Tự động xóa sạch nhật ký UI
                for i in range(rest_duration, 0, -1):
                    if not self.is_running: break
                    self.root.after(0, lambda sec=i: self.countdown_label.config(text=f"Nghỉ: {sec}s"))
                    time.sleep(1)
                self.root.after(0, lambda: self.countdown_label.config(text=""))
                if self.is_running:
                    self.log("Đã nghỉ xong, chuẩn bị Reset Wi-Fi lấy IP mới để chạy tiếp...")
                    self.reconnect_wifi_windows(wifi)

        self.is_running = False
        self.root.after(0, lambda: self.set_buttons_state(False))
        self.log("=== ĐÃ DỪNG HOÀN TOÀN ===")

    def run_single_driver(self, driver, url):
        short_url = url[-8:] if len(url) > 8 else url
        try:
            # Dọn dẹp RAM: Đóng các tab quảng cáo thừa
            if len(driver.window_handles) > 1:
                main_window = driver.window_handles[0]
                for handle in driver.window_handles[1:]:
                    driver.switch_to.window(handle)
                    driver.close()
                driver.switch_to.window(main_window)
        except Exception:
            pass

        self.log(f"[{short_url}] Đang mở URL...")
        try:
            driver.delete_all_cookies()
        except Exception:
            pass
        
        while self.is_running:
            try:
                driver.get(url)
                break
            except Exception:
                if not self.is_running: return
                time.sleep(0.03) # Tăng tốc x2
        
        timeout = 10 # Tăng tốc x2: Giảm thời gian chờ tối đa 1 vòng lặp từ 30s xuống 15s
        start_time = time.time()
        is_redirected = False
        omg_clicked = False
        
        while self.is_running and (time.time() - start_time < timeout):
            try:
                # Bọc try-except toàn bộ để không bị crash bởi lỗi vặt
                current_url = driver.current_url
                if "google.com" in current_url:
                    is_redirected = True
                    break
                    
                if "omg10.com/afu.php" in current_url and not omg_clicked:
                    self.log(f"[{short_url}] Nhận diện omg10.com, tự động click...")
                    body = driver.find_element(By.TAG_NAME, "body")
                    driver.execute_script("arguments[0].click();", body)
                    omg_clicked = True
                    time.sleep(0.03) # Tăng tốc x2
                    continue
                    
                # Tối ưu hóa: Lọc iframe bằng XPath thay vì duyệt tất cả qua Selenium, giúp giảm hàng chục API calls và tăng tốc 1.5-2 lần mỗi vòng
                iframes = driver.find_elements(By.XPATH, "//iframe[contains(@src, 'turnstile') or contains(@src, 'challenge') or contains(translate(@title, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cloudflare')]")
                for iframe in iframes:
                    try:
                        driver.switch_to.frame(iframe)
                        js_checkbox = """
                        var cbs = document.querySelectorAll('input[type="checkbox"], .checkbox, .mark, [id*="checkbox"]');
                        for (var i = 0; i < cbs.length; i++) {
                            if (cbs[i].offsetWidth > 0 || cbs[i].offsetHeight > 0) {
                                cbs[i].click();
                                return true;
                            }
                        }
                        return false;
                        """
                        if driver.execute_script(js_checkbox):
                            self.log(f"[{short_url}] Đã tick Cloudflare/Captcha!")
                            time.sleep(0.03) # Tăng tốc x2
                            break
                    except Exception:
                        pass
                    finally:
                        driver.switch_to.default_content()

                js_click_btn = """
                var keywords = ['verify', 'human', 'xác minh', 'xác thực', 'continue', 'tiếp tục'];
                var btns = document.querySelectorAll('button, a, div[class*="btn"]');
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].offsetWidth > 0 || btns[i].offsetHeight > 0) {
                        var text = (btns[i].innerText || btns[i].textContent || '').toLowerCase();
                        if (keywords.some(function(kw) { return text.includes(kw); })) {
                            btns[i].click();
                            return true;
                        }
                    }
                }
                return false;
                """
                if driver.execute_script(js_click_btn):
                    self.log(f"[{short_url}] Đã click nút xác minh.")
                    time.sleep(0.03) # Tăng tốc x2
            except Exception:
                pass
            
            time.sleep(0.020) # Tăng tốc x2: Quét phần tử trên web cực nhanh với chu kỳ 0.025s
        
        if not self.is_running:
            return

        if is_redirected:
            self.log(f"[{short_url}] -> Đã tới Google!")
        else:
            self.log(f"[{short_url}] -> Hết thời gian chờ nhưng chưa tới Google. Thử lại...")

if __name__ == "__main__":
    root = tk.Tk()
    app = DirectLinkApp(root)
    root.mainloop()