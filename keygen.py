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
        
        tk.Label(root, text="Thời gian hết hạn (Năm - Tháng - Ngày   Giờ : Phút):", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        
        # Khung chứa các ô nhập ngày tháng
        exp_frame = tk.Frame(root)
        exp_frame.pack(pady=5)
        
        default_date = datetime.datetime.now() + datetime.timedelta(days=30)
        
        # Hàm chặn không cho gõ chữ, chỉ cho gõ số
        def validate_num(P):
            return P == "" or P.isdigit()
        vcmd = (root.register(validate_num), '%P')
        
        self.year_var = tk.StringVar(value=default_date.strftime("%Y"))
        self.month_var = tk.StringVar(value=default_date.strftime("%m"))
        self.day_var = tk.StringVar(value=default_date.strftime("%d"))
        self.hour_var = tk.StringVar(value=default_date.strftime("%H"))
        self.minute_var = tk.StringVar(value=default_date.strftime("%M"))
        
        tk.Entry(exp_frame, textvariable=self.year_var, width=5, font=("Arial", 10), justify="center", validate="key", validatecommand=vcmd).pack(side="left")
        tk.Label(exp_frame, text="-", font=("Arial", 10, "bold")).pack(side="left")
        
        tk.Entry(exp_frame, textvariable=self.month_var, width=3, font=("Arial", 10), justify="center", validate="key", validatecommand=vcmd).pack(side="left")
        tk.Label(exp_frame, text="-", font=("Arial", 10, "bold")).pack(side="left")
        
        tk.Entry(exp_frame, textvariable=self.day_var, width=3, font=("Arial", 10), justify="center", validate="key", validatecommand=vcmd).pack(side="left")
        tk.Label(exp_frame, text="   ", font=("Arial", 10, "bold")).pack(side="left")
        
        tk.Entry(exp_frame, textvariable=self.hour_var, width=3, font=("Arial", 10), justify="center", validate="key", validatecommand=vcmd).pack(side="left")
        tk.Label(exp_frame, text=":", font=("Arial", 10, "bold")).pack(side="left")
        
        tk.Entry(exp_frame, textvariable=self.minute_var, width=3, font=("Arial", 10), justify="center", validate="key", validatecommand=vcmd).pack(side="left")
        
        tk.Button(root, text="Tạo Key", bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=15, command=self.on_generate).pack(pady=20)
        
        tk.Label(root, text="Key tạo thành công (Copy gửi cho khách):", font=("Arial", 10, "bold")).pack(pady=(5, 5))
        self.key_text = tk.Text(root, height=3, width=55, font=("Arial", 10))
        self.key_text.pack(pady=5)
        
        tk.Button(root, text="Copy Key", bg="#2196F3", fg="white", font=("Arial", 9, "bold"), command=self.copy_key).pack(pady=5)

    def on_generate(self):
        hwid = self.hwid_entry.get().strip()
        
        # Lấy giá trị từng ô và tự động thêm số 0 đằng trước nếu khách nhập 1 chữ số (VD: tháng 7 -> 07)
        y = self.year_var.get().strip()
        m = self.month_var.get().strip().zfill(2)
        d = self.day_var.get().strip().zfill(2)
        h = self.hour_var.get().strip().zfill(2)
        minute = self.minute_var.get().strip().zfill(2)
        
        exp = f"{y}-{m}-{d} {h}:{minute}"
        
        if not hwid:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập mã HWID của khách!")
            return
            
        try:
            datetime.datetime.strptime(exp, "%Y-%m-%d %H:%M")
            key = generate_key(hwid, exp)
            self.key_text.delete(1.0, tk.END)
            self.key_text.insert(tk.END, key)
        except ValueError:
            messagebox.showwarning("Lỗi định dạng", "Ngày giờ nhập vào không hợp lệ!\nVui lòng kiểm tra lại.")
            
    def copy_key(self):
        key = self.key_text.get(1.0, tk.END).strip()
        if key:
            self.root.clipboard_clear()
            self.root.clipboard_append(key)

if __name__ == "__main__":
    root = tk.Tk()
    app = KeyGenApp(root)
    root.mainloop()