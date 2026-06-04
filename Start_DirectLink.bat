@echo off

:: Yêu cầu quyền Administrator (Bắt buộc cho Ethernet MAC spoofing)
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /B
)

:: Di chuyển working directory vào đúng thư mục DirectLink
cd /d "c:\Users\Admin\OneDrive\Desktop\3,8s"

:: Chạy file python và hiện terminal
python main.py
pause