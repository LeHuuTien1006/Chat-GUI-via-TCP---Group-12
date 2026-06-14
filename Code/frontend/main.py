import sys
import json
import struct
import socket
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer, QThread, Signal

class SocketWorker(QThread):
    status_update = Signal(str)
    login_success = Signal(str)
    login_error = Signal(str)

    def __init__(self, host='127.0.0.1', port=9999, user_data=None):
        super().__init__()
        self.host = host
        self.port = port
        self.user_data = user_data or {"type": "login", "nickname": "Frontend_Dev"}

    def run(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)  
            sock.connect((self.host, self.port))

            json_str = json.dumps(self.user_data)
            payload = json_str.encode('utf-8')
            
            header = struct.pack("!I", len(payload))
            
            sock.sendall(header + payload)
            
            reply_header = sock.recv(4)
            if len(reply_header) == 4:
                reply_size = struct.unpack("!I", reply_header)[0]
                
                reply_payload = sock.recv(reply_size)
                reply_json = json.loads(reply_payload.decode('utf-8'))
                
                if reply_json.get("type") == "info" and reply_json.get("msg") == "OK":
                    self.login_success.emit("Đăng nhập thành công!")
                else:
                    self.login_error.emit("Đăng nhập thất bại từ server.")
            
            sock.close()

        except ConnectionRefusedError:
            self.login_error.emit("Không thể kết nối. Server chưa bật!")
        except Exception as e:
            self.login_error.emit(f"Lỗi mạng: {str(e)}")

class LoginWindow(QWidget): 
    def __init__(self):
        super().__init__()
        
        loader = QUiLoader()
        ui_file = QFile("loginUI.ui") 
        
        if not ui_file.open(QFile.ReadOnly):
            print(f"Không thể mở file UI: {ui_file.errorString()}")
            sys.exit(-1)
            
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        self.setFixedSize(831, 486)

        self.ui.label_readytochat.setText("")
        
        self.timer = QTimer(self)
        self.dot_count = 0
        self.timer.timeout.connect(self.update_dots)

        self.ui.pushButton_enter.clicked.connect(self.start_connecting)

    def start_connecting(self):
        self.dot_count = 0
        self.ui.label_readytochat.setText("Ready to connect")
        self.timer.start(500) 

    def update_dots(self):
        self.dot_count += 1
        if self.dot_count > 3:
            self.dot_count = 0
        
        dots = "." * self.dot_count
        self.ui.label_readytochat.setText(f"Ready to connect{dots}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec())