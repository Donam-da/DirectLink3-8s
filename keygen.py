import hmac
import hashlib
import base64
import json
import datetime
import tkinter as tk
from tkinter import messagebox

# LƯU Ý: SECRET_KEY NÀY PHẢI GIỐNG HỆT BÊN MAIN.PY
SECRET_KEY = b"THAY_DOI_CHUOI_NAY_THANH_MAT_KHAU_CUA_BAN"

def generate_key(hwid, expiry_date):
    data = {"hwid": hwid, "exp": expiry_date}
    data_str = json.dumps(data)
    # Tạo chữ ký để chống làm giả nội dung
    signature = hmac.new(SECRET_KEY, data_str.encode('utf-8'), hashlib.sha256).hexdigest()
    
    payload = {"data": data_str, "sig": signature}
    # Mã hóa Base64 để tạo ra Key dạng chuỗi ký tự
    key = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')
    return key

class KeyGenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Phần mềm tạo Key kích hoạt")
        self.root.geometry("500x380")
        
        tk.Label(root, text="Mã máy (HWID) của khách:", font=("Arial", 10, "bold")).pack(pady=(20, 5))
        self.hwid_entry = tk.Entry(root, width=50, font=("Arial", 10))
        self.hwid_entry.pack(pady=5)
        
        tk.Label(root, text="Thời gian hết hạn (YYYY-MM-DD HH:MM):", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        self.exp_entry = tk.Entry(root, width=25, font=("Arial", 10), justify="center")
        self.exp_entry.pack(pady=5)
        
        # Tự động gợi ý hạn sử dụng là 30 ngày kể từ hôm nay
        default_exp = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M")
        self.exp_entry.insert(0, default_exp)
        
        tk.Button(root, text="Tạo Key", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=15, command=self.on_generate).pack(pady=20)
        
        tk.Label(root, text="Key tạo thành công (Copy gửi cho khách):", font=("Arial", 10, "bold")).pack(pady=(5, 5))
        self.key_text = tk.Text(root, height=4, width=55, font=("Arial", 10))
        self.key_text.pack(pady=5)
        
        tk.Button(root, text="Copy Key", bg="#2196F3", fg="white", font=("Arial", 9, "bold"), command=self.copy_key).pack(pady=5)

    def on_generate(self):
        hwid = self.hwid_entry.get().strip()
        exp = self.exp_entry.get().strip()
        
        if not hwid:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập mã HWID của khách!")
            return
            
        try:
            datetime.datetime.strptime(exp, "%Y-%m-%d %H:%M")
            key = generate_key(hwid, exp)
            self.key_text.delete(1.0, tk.END)
            self.key_text.insert(tk.END, key)
        except ValueError:
            messagebox.showwarning("Lỗi định dạng", "Định dạng không đúng!\nVui lòng nhập theo dạng YYYY-MM-DD HH:MM\nVí dụ: 2024-12-31 15:30")
            
    def copy_key(self):
        key = self.key_text.get(1.0, tk.END).strip()
        if key:
            self.root.clipboard_clear()
            self.root.clipboard_append(key)
            messagebox.showinfo("Thành công", "Đã copy Key vào khay nhớ tạm!")

if __name__ == "__main__":
    root = tk.Tk()
    app = KeyGenApp(root)
    root.mainloop()