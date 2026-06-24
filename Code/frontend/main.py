import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
multimedia_dir = os.path.abspath(os.path.join(current_dir, '..', 'Multimedia'))

if multimedia_dir not in sys.path:
    sys.path.insert(0, multimedia_dir)

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
        self.nickname = nickname
        
        # 1. SỬA ĐƯỜNG DẪN TUYỆT ĐỐI CHO FILE UI PHÒNG CHAT
        import os
        from PySide6.QtUiTools import QUiLoader
        from PySide6.QtCore import QFile
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, "mainchatUI.ui")
        
        loader = QUiLoader()
        ui_file = QFile(ui_path) 
        if not ui_file.open(QFile.ReadOnly):
            print(f"Không thể mở file UI phòng chat: {ui_file.errorString()}")
            sys.exit(-1)
            
        self.ui = loader.load(ui_file)
        ui_file.close()

        # Layout và kích thước cửa sổ
        from PySide6.QtWidgets import QVBoxLayout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.ui)

        self.resize(1100, 700)
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
        self.setMinimumWidth(550)

        # 2. KHỞI TẠO CHAT BROWSER VÀ CÁC LUỒNG SỰ KIỆN (CHỈ KHỞI TẠO 1 LẦN DUY NHẤT Ở ĐÂY)
        from PySide6.QtWidgets import QVBoxLayout
        from PySide6.QtCore import Qt

        self.chat_layout = QVBoxLayout(self.ui.scrollAreaWidgetContents_2)
        self.chat_layout.setAlignment(Qt.AlignTop) # Đảm bảo tin nhắn dồn từ trên xuống
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(5)

        self.ui.btn_send.clicked.connect(self.send_message)
        self.ui.txt_input_message.returnPressed.connect(self.send_message)
        self.ui.btn_camera.clicked.connect(self.capture_and_send_image)

        # Khởi chạy luồng nhận dữ liệu từ server
        self.receiver = ReceiveThread(self.sock)
        self.receiver.message_received.connect(self.display_message)
        self.receiver.image_received.connect(self.display_image)
        self.receiver.start()
        
        self.ui.lbl_chat_title.setText(f"Chào mừng, {self.nickname}!")
        
        self.engine = MessageSearchEngine()
        self.msg_counter = 0 

        self.ui.txt_search.textChanged.connect(self.perform_global_search) 
        self.ui.btn_search_chat.clicked.connect(self.show_local_search_input) 

        self.last_sender = None
        self.last_msg_time = None
        self.last_time_label = None

        # 3. CHẠY HÀM TẠO TAB ĐỘNG CỦA CỘT 2
        self.setup_dynamic_tabs()

    def setup_dynamic_tabs(self):
        from PySide6.QtWidgets import QTabWidget, QListWidget

        # Khởi tạo QTabWidget mới hoàn toàn bằng mã Python
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #22262B;
            }
            QTabBar::tab {
                background-color: #1E1F20;
                color: #8A8D91;
                padding: 8px 16px;
                border: none;
                font-size: 13px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #22262B;
                color: #ffffff;
                border-bottom: 2px solid #3498db;
            }
            QTabBar::tab:hover {
                color: #ffffff;
                background-color: rgba(255, 255, 255, 0.05);
            }
        """)

        # Tạo các QListWidget độc lập cho dữ liệu TÌM KIẾM
        self.list_all = QListWidget()                
        self.list_contacts = QListWidget()           
        self.list_messages = QListWidget()           

        list_style = "background-color: transparent; color: white; border: none; font-size: 13px;"
        self.list_all.setStyleSheet(list_style) 
        self.list_contacts.setStyleSheet(list_style)
        self.list_messages.setStyleSheet(list_style)

        # Thêm các List tương ứng vào từng trang Tab
        self.tab_widget.addTab(self.list_all, "Tất cả")
        self.tab_widget.addTab(self.list_contacts, "Liên hệ")
        self.tab_widget.addTab(self.list_messages, "Tin nhắn")

        # Đưa QTabWidget vào layout đứng của Cột 2
        self.ui.verticalLayout_2.addWidget(self.tab_widget)

        # MẶC ĐỊNH ẨN THANH TAB KHI MỚI KHỞI ĐỘNG
        self.tab_widget.hide()
        # ĐÃ XÓA TOÀN BỘ PHẦN CODE TRÙNG LẶP GÂY XUNG ĐỘT LUỒNG TẠI ĐÂY


    # --- THÊM 2 HÀM TÌM KIẾM CỤC BỘ CHO CỘT 3 VÀO ĐÂY ---
    def show_local_search_input(self):
        from PySide6.QtWidgets import QInputDialog
        keyword, ok = QInputDialog.getText(self, "Tìm kiếm cục bộ", "Nhập từ khóa cần tìm trong đoạn chat này:")
        if ok and keyword.strip():
            self.perform_local_search(keyword.strip())

    def perform_local_search(self, keyword):
        from integration import highlight_for_qt
        current_room = self.ui.lbl_chat_title.text()
        
        all_results = self.engine.search(keyword)
        # Nếu chưa chia phòng, có thể bỏ qua lọc theo current_room tạm thời
        # local_results = [r for r in all_results if r.message.room == current_room]
        local_results = all_results 
        
        self.chat_browser.append("<hr>")
        self.chat_browser.append(f"<div style='color: #f1c40f;'><b>🔍 KẾT QUẢ TÌM KIẾM TRONG ĐOẠN CHAT: '{keyword}'</b></div>")
        
        for r in local_results:
            html_content = highlight_for_qt(r.message.content, r.match_positions)
            self.chat_browser.append(f"<b>{r.message.sender}:</b> {html_content}")
        
        self.chat_browser.append("<hr>")


    def perform_global_search(self, text):
        keyword = text.strip()
        
        # Xóa sạch kết quả tìm kiếm cũ ở các tab trước khi nạp data mới
        self.list_all.clear()
        self.list_contacts.clear()
        self.list_messages.clear()

        # TRƯỜNG HỢP Ô TÌM KIẾM TRỐNG: Ẩn thanh Tab tìm kiếm, hiện lại danh sách chat gốc ban đầu
        if not keyword:
            self.tab_widget.hide()
            self.ui.list_chats.show()
            return

        # TRƯỜNG HỢP CÓ TỪ KHÓA: Ẩn danh sách chat gốc, bật thanh Tab kết quả tìm kiếm lên
        self.ui.list_chats.hide()
        self.tab_widget.show()

        # --- LUỒNG 1: TÌM KIẾM LIÊN HỆ ---
        sample_contacts = ["Lê Trần Hiền", "Bùi Minh Hiếu", "Trung Hiếu", "Vũ Thị Thu Hiền", "Tấn Hiệp", "Công Hiếu"]
        
        for contact in sample_contacts:
            if keyword.lower() in contact.lower():
                self.list_contacts.addItem(contact)
                self.list_all.addItem(f"[Liên hệ] {contact}")

        # --- LUỒNG 2: TÌM KIẾM TIN NHẮN (Gọi Engine) ---
        message_results = self.engine.search(keyword)
        
        for r in message_results:
            msg_display = f"{r.message.sender}: {r.message.content}"
            self.list_messages.addItem(msg_display)
            self.list_all.addItem(f"[Tin nhắn] {msg_display}")

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
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
        from PySide6.QtCore import Qt, QTimer
        from datetime import datetime

        current_time = datetime.now()
        display_time = current_time.strftime("%H:%M")
        
        # 1. KIỂM TRA ĐIỀU KIỆN HIỂN THỊ TAG THỜI GIAN (Cách 20 phút = 1200 giây)
        show_time_tag = False
        if self.last_msg_time is None or (current_time - self.last_msg_time).total_seconds() > 1200:
            show_time_tag = True
            self.last_sender = None  # Cắt đứt cụm, ép hiển thị lại tên người gửi

        # Tạo container dọc bọc toàn bộ khối (Tag thời gian + Tên + Bong bóng)
        msg_block = QWidget()
        block_layout = QVBoxLayout(msg_block)
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(2)

        # Vẽ Tag thời gian ở giữa màn hình
        if show_time_tag:
            tag_text = current_time.strftime("%H:%M %d/%m/%Y")
            lbl_tag = QLabel(tag_text)
            lbl_tag.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #8A8D91; font-size: 11px; padding: 4px 12px; border-radius: 10px;")
            
            tag_row = QHBoxLayout()
            tag_row.addStretch()
            tag_row.addWidget(lbl_tag)
            tag_row.addStretch()
            block_layout.addLayout(tag_row)
            block_layout.addSpacing(8) # Cách bong bóng chat một khoảng

        # 2. VẼ TÊN NGƯỜI GỬI BÊN NGOÀI BONG BÓNG (Chỉ vẽ ở tin đầu tiên của cụm, không vẽ cho "Tôi")
        if sender != "Tôi" and sender != self.last_sender:
            lbl_name = QLabel(sender)
            lbl_name.setStyleSheet("color: #8A8D91; font-size: 12px; margin-left: 10px; margin-bottom: 2px;")
            name_row = QHBoxLayout()
            name_row.addWidget(lbl_name)
            name_row.addStretch()
            block_layout.addLayout(name_row)

        # 3. ẨN THỜI GIAN CỦA TIN NHẮN TRƯỚC ĐÓ (Nếu cùng 1 người gửi trong cụm)
        if sender == self.last_sender and not show_time_tag:
            if self.last_time_label is not None:
                self.last_time_label.hide()

        # 4. VẼ BONG BÓNG TIN NHẮN
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        bubble = QWidget()
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.setSpacing(4)

        # Nội dung chữ
        lbl_text = QLabel(content)
        lbl_text.setWordWrap(True)
        lbl_text.setStyleSheet("background: transparent; color: white; font-size: 14px;")

        # --- ĐOẠN CODE MỚI ĐỂ CHỐNG LÒ XO ÉP XUỐNG DÒNG ---
        from PySide6.QtGui import QFontMetrics
        
        # Đo chiều dài thực tế của text với font hiện tại
        fm = lbl_text.fontMetrics()
        # Giả lập vẽ đoạn chữ ra với giới hạn ngang 500px, dọc 2000px để lấy kích thước
        rect = fm.boundingRect(0, 0, 500, 2000, Qt.TextWordWrap, content)
        
        # Cài đặt bộ khung cứng: MinimumWidth giúp nó không bị co lại, MaximumWidth giữ giới hạn 500px
        lbl_text.setMinimumWidth(rect.width() + 5)
        lbl_text.setMaximumWidth(500)
        # --------------------------------------------------
        
        bubble_layout.addWidget(lbl_text)

        lbl_time = QLabel(display_time)
        lbl_time.setStyleSheet("background: transparent; color: #8A8D91; font-size: 11px;")
        bubble_layout.addWidget(lbl_time)

        if sender == "Tôi":
            lbl_time.setAlignment(Qt.AlignRight)
            bubble.setStyleSheet("QWidget { background-color: #1E6C93; border-radius: 15px; }")
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        else:
            lbl_time.setAlignment(Qt.AlignLeft)
            bubble.setStyleSheet("QWidget { background-color: #2C323A; border-radius: 15px; }")
            row_layout.addWidget(bubble)
            row_layout.addStretch()

        block_layout.addWidget(row_widget)
        self.chat_layout.addWidget(msg_block)

        # 5. CẬP NHẬT TRÍ NHỚ CHO LẦN HIỂN THỊ SAU
        self.last_sender = sender
        self.last_msg_time = current_time
        self.last_time_label = lbl_time

        # Cuộn màn hình
        QTimer.singleShot(50, lambda: self.ui.scroll_chat_history.verticalScrollBar().setValue(
            self.ui.scroll_chat_history.verticalScrollBar().maximum()
        ))

        # Lưu vào Engine (Giữ nguyên code cũ của em)
        self.msg_counter += 1
        full_timestamp = datetime.now().strftime("%H:%M:%S")
        from integration import Message
        msg_obj = Message(
            msg_id=self.msg_counter, 
            sender=sender, 
            content=content, 
            timestamp=full_timestamp
        )
        self.engine.add_message(msg_obj)

    def display_image(self, frame, is_sender=False):
        import cv2
        from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
        from PySide6.QtGui import QImage, QPixmap
        from PySide6.QtCore import Qt, QTimer
        from datetime import datetime

        sender = "Tôi" if is_sender else "Người khác"
        current_time = datetime.now()
        display_time = current_time.strftime("%H:%M")

        show_time_tag = False
        if self.last_msg_time is None or (current_time - self.last_msg_time).total_seconds() > 1200:
            show_time_tag = True
            self.last_sender = None

        msg_block = QWidget()
        block_layout = QVBoxLayout(msg_block)
        block_layout.setContentsMargins(0, 0, 0, 0)
        block_layout.setSpacing(2)

        if show_time_tag:
            tag_text = current_time.strftime("%H:%M %d/%m/%Y")
            lbl_tag = QLabel(tag_text)
            lbl_tag.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); color: #8A8D91; font-size: 11px; padding: 4px 12px; border-radius: 10px;")
            tag_row = QHBoxLayout()
            tag_row.addStretch()
            tag_row.addWidget(lbl_tag)
            tag_row.addStretch()
            block_layout.addLayout(tag_row)
            block_layout.addSpacing(8)

        if sender != "Tôi" and sender != self.last_sender:
            lbl_name = QLabel(sender)
            lbl_name.setStyleSheet("color: #8A8D91; font-size: 12px; margin-left: 10px; margin-bottom: 2px;")
            name_row = QHBoxLayout()
            name_row.addWidget(lbl_name)
            name_row.addStretch()
            block_layout.addLayout(name_row)

        if sender == self.last_sender and not show_time_tag:
            if self.last_time_label is not None:
                self.last_time_label.hide()

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        
        if pixmap.width() > 250:
            pixmap = pixmap.scaledToWidth(250, Qt.SmoothTransformation)

        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        bubble = QWidget()
        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(10, 10, 10, 10)

        lbl_img = QLabel()
        lbl_img.setPixmap(pixmap)
        lbl_img.setStyleSheet("background: transparent;")

        lbl_time = QLabel(display_time)
        lbl_time.setStyleSheet("background: transparent; color: #D0D0D0; font-size: 11px;")

        if is_sender:
            lbl_time.setAlignment(Qt.AlignRight)
            bubble_layout.addWidget(lbl_img)
            bubble_layout.addWidget(lbl_time)
            bubble.setStyleSheet("QWidget { background-color: #1E6C93; border-radius: 15px; }")
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        else:
            lbl_time.setAlignment(Qt.AlignLeft)
            bubble_layout.addWidget(lbl_img)
            bubble_layout.addWidget(lbl_time)
            bubble.setStyleSheet("QWidget { background-color: #2C323A; border-radius: 15px; }")
            row_layout.addWidget(bubble)
            row_layout.addStretch()

        block_layout.addWidget(row_widget)
        self.chat_layout.addWidget(msg_block)

        self.last_sender = sender
        self.last_msg_time = current_time
        self.last_time_label = lbl_time

        QTimer.singleShot(50, lambda: self.ui.scroll_chat_history.verticalScrollBar().setValue(self.ui.scroll_chat_history.verticalScrollBar().maximum()))

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

    def resizeEvent(self, event):
        # Gọi hàm gốc để đảm bảo các xử lý mặc định của QWidget vẫn hoạt động
        super().resizeEvent(event)

        current_width = self.width()

        # 1. Xử lý cột 4 (Thông tin) - Ẩn khi nhỏ hơn 1220px
        if current_width < 1220:
            self.ui.col4_info.hide()
        else:
            self.ui.col4_info.show()

        # 2. Xử lý cột 2 (Danh sách chat) - Ẩn khi nhỏ hơn 870px
        if current_width < 870:
            self.ui.col2_chatlist.hide()
        else:
            self.ui.col2_chatlist.show()

class LoginWindow(QWidget): 
    def __init__(self):
        super().__init__()
        
        import os
        from PySide6.QtUiTools import QUiLoader
        from PySide6.QtCore import QFile
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, "loginUI.ui")
        
        loader = QUiLoader()
        ui_file = QFile(ui_path) 
        
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