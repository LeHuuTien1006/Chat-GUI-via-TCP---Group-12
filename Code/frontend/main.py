import sys
import json
import struct
import socket
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QTextBrowser, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QFile, QTimer, QThread, Signal

class SocketWorker(QThread):
    status_update = Signal(str)
    login_success = Signal(object, str)
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

            # Gói dữ liệu login
            json_str = json.dumps(self.user_data)
            payload = json_str.encode('utf-8')
            header = struct.pack("!I", len(payload))
            sock.sendall(header + payload)

            # Chờ phản hồi từ server
            reply_header = sock.recv(4)
            if len(reply_header) == 4:
                reply_size = struct.unpack("!I", reply_header)[0]
                reply_payload = sock.recv(reply_size)
                reply_json = json.loads(reply_payload.decode('utf-8'))
                
                if reply_json.get("type") == "info" and reply_json.get("msg") == "OK":
                    # THÀNH CÔNG: Gỡ bỏ timeout để socket rảnh rỗi chờ chat
                    sock.settimeout(None) 
                    # Phát tín hiệu mang theo đối tượng socket ra ngoài (KHÔNG GỌI sock.close())
                    self.login_success.emit(sock, "Đăng nhập thành công!")
                    return
                else:
                    self.login_error.emit("Đăng nhập thất bại từ server.")
                    sock.close()
            else:
                self.login_error.emit("Server phản hồi sai định dạng.")
                sock.close()

        except ConnectionRefusedError:
            self.login_error.emit("Không thể kết nối. Server chưa bật!")
        except Exception as e:
            self.login_error.emit(f"Lỗi mạng: {str(e)}")

# -------------------------------------------------------------
# LUỒNG LẮNG NGHE TIN NHẮN TỪ SERVER
# -------------------------------------------------------------
class ReceiveThread(QThread):
    message_received = Signal(str, str) # Tín hiệu phát ra: (người_gửi, nội_dung)

    def __init__(self, sock):
        super().__init__()
        self.sock = sock
        self._is_running = True

    def run(self):
        while self._is_running:
            try:
                # 1. Nhận 4-byte header để biết kích thước gói tin
                header = b""
                while len(header) < 4:
                    chunk = self.sock.recv(4 - len(header))
                    if not chunk:
                        return
                    header += chunk
                
                size = struct.unpack("!I", header)[0]
                
                # 2. Nhận đủ dữ liệu (payload)
                payload = b""
                while len(payload) < size:
                    chunk = self.sock.recv(size - len(payload))
                    if not chunk:
                        return
                    payload += chunk
                    
                # 3. Phân loại dữ liệu
                try:
                    text = payload.decode('utf-8')
                    data = json.loads(text)
                    
                    # Nếu server báo có tin nhắn mới thì báo ra ngoài giao diện
                    if data.get("type") == "new_message":
                        self.message_received.emit(data["sender"], data["content"])
                except UnicodeDecodeError:
                    # Gặp lỗi decode nghĩa là đây là file ảnh (Binary)
                    # Anh em mình sẽ xử lý phần ảnh ở bước sau
                    pass
            except Exception as e:
                print("[ReceiveThread] Lỗi nhận dữ liệu:", e)
                break

# 2. CỬA SỔ PHÒNG CHAT (CHÍNH)
class ChatWindow(QWidget):
    def __init__(self, sock, nickname):
        super().__init__()
        self.sock = sock 
        self.nickname = nickname # Nhận tên từ màn hình đăng nhập
        
        loader = QUiLoader()
        ui_file = QFile("mainchatUI.ui") 
        if not ui_file.open(QFile.ReadOnly):
            print(f"Không thể mở file UI phòng chat: {ui_file.errorString()}")
            sys.exit(-1)
            
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # 1. Khởi tạo khung hiển thị văn bản chat (QTextBrowser)
        self.chat_browser = QTextBrowser()
        self.chat_browser.setStyleSheet("background-color: transparent; color: white; border: none; font-size: 14px;")
        layout = QVBoxLayout(self.ui.scrollAreaWidgetContents_2)
        layout.addWidget(self.chat_browser)

        # 2. Gắn sự kiện gửi tin nhắn khi bấm nút hoặc ấn Enter
        self.ui.btn_send.clicked.connect(self.send_message)
        self.ui.txt_input_message.returnPressed.connect(self.send_message)

        # 3. Khởi chạy luồng nhận tin nhắn liên tục
        self.receiver = ReceiveThread(self.sock)
        self.receiver.message_received.connect(self.display_message)
        self.receiver.start()
        
        self.ui.lbl_chat_title.setText(f"Chào mừng, {self.nickname}!")

    def send_message(self):
        content = self.ui.txt_input_message.text().strip()
        if not content:
            return

        # Đóng gói JSON và 4-byte header theo đúng chuẩn PM dặn
        msg_dict = {"type": "chat_all", "sender": self.nickname, "content": content}
        payload = json.dumps(msg_dict).encode('utf-8')
        header = struct.pack("!I", len(payload))

        try:
            self.sock.sendall(header + payload)
            # In ra màn hình của chính mình trước
            self.display_message("Tôi", content)
            self.ui.txt_input_message.clear()
            print(f"[LOG] Đã gửi JSON: {msg_dict}")
        except Exception as e:
            print("Lỗi gửi tin nhắn:", e)

    def display_message(self, sender, content):
        # Định dạng và in tin nhắn lên khung chat
        color = "#3498db" if sender == "Tôi" else "#e74c3c"
        html_msg = f'<div style="margin-bottom: 5px;"><b><span style="color:{color};">{sender}:</span></b> {content}</div>'
        self.chat_browser.append(html_msg)

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

        # Lấy thông tin từ giao diện để cấu hình kết nối
        ip = self.ui.lineEdit_ipnum.text()
        port = int(self.ui.lineEdit_portnum.text())
        nickname = self.ui.lineEdit_inputnickname.text().strip()

        if not nickname:
            self.ui.label_readytochat.setText("Vui lòng nhập biệt danh!")
            self.timer.stop()
            return
            
        user_data = {"type": "login", "nickname": nickname}
        
        # Khởi tạo và chạy luồng mạng
        self.worker = SocketWorker(host=ip, port=port, user_data=user_data)
        self.worker.login_success.connect(self.handle_login_success)
        self.worker.login_error.connect(self.handle_login_error)
        self.worker.start()

    def handle_login_success(self, sock, msg):
        self.timer.stop()
        self.ui.label_readytochat.setText(msg)
        
        # Lấy nickname để truyền sang phòng chat
        nickname = self.ui.lineEdit_inputnickname.text().strip()
        
        self.hide()                          
        self.chat_window = ChatWindow(sock, nickname) # Khởi tạo kèm tên người dùng
        self.chat_window.show()              # Hiển thị cửa sổ chat

    def handle_login_error(self, msg):
        self.timer.stop()
        self.ui.label_readytochat.setText(msg)

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