import sys
import os



import json
import struct
import socket
import numpy as np
import cv2
import base64
from datetime import datetime
from integration import MessageSearchEngine, Message
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox, QTextBrowser, QVBoxLayout, QLabel
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QFile, QTimer, QThread, Signal, Qt

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

# LUỒNG LẮNG NGHE TIN NHẮN TỪ SERVER
class ReceiveThread(QThread):
    message_received = Signal(str, str) # Tín hiệu phát ra: (người_gửi, nội_dung)
    image_received = Signal(object)

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
                    # Sử dụng logic giải mã từ OpenCV
                    buffer = np.frombuffer(payload, dtype=np.uint8)
                    frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
                    
                    if frame is not None:
                        self.image_received.emit(frame) # Phát tín hiệu ảnh ra ngoài
                    pass
            except Exception as e:
                print("[ReceiveThread] Lỗi nhận dữ liệu:", e)
                break

# LUỒNG CHỤP ẢNH TỪ WEBCAM (TRÁNH ĐƠ GIAO DIỆN)
class CameraThread(QThread):
    image_encoded = Signal(bytes) # Tín hiệu mang mảng byte của ảnh
    error_occurred = Signal(str)

    def run(self):
        try:
            # 1. Mở camera mặc định (index = 0)
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.error_occurred.emit("Không thể kết nối với Webcam!")
                return
            
            # 2. Chụp 1 khung hình rồi tắt camera ngay
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                self.error_occurred.emit("Chụp ảnh thất bại!")
                return

            # 3. Nén ảnh thành chuẩn JPEG để giảm dung lượng mạng
            success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if success:
                # Chuyển thành dạng byte và phát tín hiệu ra ngoài
                self.image_encoded.emit(buffer.tobytes())
            else:
                self.error_occurred.emit("Lỗi mã hóa ảnh!")
        except Exception as e:
            self.error_occurred.emit(f"Lỗi Camera: {str(e)}")

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

        self.ui.btn_camera.clicked.connect(self.capture_and_send_image)

        # 3. Khởi chạy luồng nhận tin nhắn liên tục
        self.receiver = ReceiveThread(self.sock)
        self.receiver.message_received.connect(self.display_message)
        
        # Kết nối tín hiệu nhận ảnh
        self.receiver.image_received.connect(self.display_image)
        self.receiver.start()
        
        self.ui.lbl_chat_title.setText(f"Chào mừng, {self.nickname}!")
        # Khởi tạo bộ máy tìm kiếm tin nhắn
        self.engine = MessageSearchEngine()
        self.msg_counter = 0 # Biến tạo ID tự tăng cho tin nhắn

        # Gắn sự kiện cho nút tìm kiếm và khi ấn Enter ở ô tìm kiếm
        self.ui.btn_search_chat.clicked.connect(self.perform_search)
        self.ui.txt_search.returnPressed.connect(self.perform_search)


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
        # 1. Định dạng và in tin nhắn lên khung chat (code cũ của em)
        color = "#3498db" if sender == "Tôi" else "#e74c3c"
        html_msg = f'<div style="margin-bottom: 5px;"><b><span style="color:{color};">{sender}:</span></b> {content}</div>'
        self.chat_browser.append(html_msg)

        # 2. Đóng gói tin nhắn vào Object Message và lưu vào Engine (code mới thêm)
        self.msg_counter += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Tạo đối tượng Message chuẩn theo API của Tiến
        msg_obj = Message(
            msg_id=self.msg_counter, 
            sender=sender, 
            content=content, 
            timestamp=timestamp
        )
        self.engine.add_message(msg_obj)

    def display_image(self, frame, is_sender=False):
        # 1. Nén ảnh thành Base64 (chuỗi ký tự) để nhúng vào HTML
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            return
            
        b64_str = base64.b64encode(buffer).decode('utf-8')
        
        # 2. Phân biệt màu sắc người gửi và người nhận
        sender = "Tôi" if is_sender else "Người khác"
        color = "#3498db" if is_sender else "#e74c3c"
        
        # 3. Ép ảnh vào khung chat bằng thẻ HTML <img> kèm giới hạn chiều rộng 250px (chống vỡ layout)
        html_msg = f'<div style="margin-bottom: 5px;"><b><span style="color:{color};">{sender}:</span></b><br><img src="data:image/jpeg;base64,{b64_str}" width="250"></div>'
        self.chat_browser.append(html_msg)

    def perform_search(self):
        # 1. Lấy từ khóa người dùng nhập
        keyword = self.ui.txt_search.text().strip()
        
        if not keyword:
            self.display_message("Hệ thống", "Vui lòng nhập từ khóa vào ô tìm kiếm!")
            return

        # 2. Gọi hàm tìm kiếm của Tiến, trả về danh sách HTML đã bôi vàng
        results_html = self.engine.get_qt_html_results(keyword)
        
        # 3. Hiển thị kết quả ra màn hình (ngăn cách bằng đường kẻ <hr>)
        self.chat_browser.append("<hr>")
        self.chat_browser.append(f"<div style='color: #f1c40f;'><b>🔍 KẾT QUẢ TÌM KIẾM CHO: '{keyword}' ({len(results_html)} kết quả)</b></div>")
        
        if len(results_html) == 0:
            self.chat_browser.append("<i>Không tìm thấy tin nhắn nào khớp.</i>")
        else:
            for html_line in results_html:
                self.chat_browser.append(html_line)
                
        self.chat_browser.append("<hr>")

    def capture_and_send_image(self):
        # Vô hiệu hóa nút tạm thời để tránh click liên tục
        self.ui.btn_camera.setEnabled(False)
        self.display_message("Hệ thống", "Đang mở camera chụp ảnh...")
        
        # Khởi chạy luồng camera
        self.camera_thread = CameraThread()
        self.camera_thread.image_encoded.connect(self.send_image_bytes)
        self.camera_thread.error_occurred.connect(lambda err: self.display_message("Lỗi", err))
        self.camera_thread.finished.connect(lambda: self.ui.btn_camera.setEnabled(True))
        self.camera_thread.start()

    def send_image_bytes(self, img_bytes):
        # Đóng gói ảnh kèm header 4-byte
        header = struct.pack("!I", len(img_bytes))
        
        try:
            self.sock.sendall(header + img_bytes)
            print(f"[LOG] Đã gửi ảnh thành công, dung lượng: {len(img_bytes)} bytes")
            
            # Giải mã chính byte ảnh mình vừa chụp để in lên khung chat của bản thân
            buffer = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
            self.display_image(frame, is_sender=True) 
            
        except Exception as e:
            print("Lỗi gửi ảnh:", e)
            self.display_message("Lỗi", "Không thể gửi ảnh!")

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