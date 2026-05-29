"""
Module tích hợp - API cho Quân (Server) và Quỳnh Anh (UI)
Nhóm 12 - Lê Hữu Tiến
────────────────────────────────────────────────────────────
File này export các hàm/class để:
  • Quân dùng: ImageSender — gửi ảnh từ Server đến Client
  • Quỳnh Anh dùng: ImageReceiver, MessageSearchEngine — tích hợp UI
────────────────────────────────────────────────────────────
"""

# ── Re-export từ các module riêng ────────────────────────────
from task2_opencv.camera_encode import (
    open_camera,
    capture_frame,
    release_camera,
    encode_frame_to_bytes,
    decode_bytes_to_frame,
    frame_to_bytes_pipeline,
)

from task2_opencv.tcp_image_transfer import (
    send_image,
    receive_image,
    recv_exact,
)

from task1_search.message_search import (
    Message,
    SearchResult,
    search_messages,
    highlight_for_qt,
)

import socket
import threading
import cv2
import numpy as np
from typing import Callable, Optional, List


# ─────────────────────────────────────────────────────────────
#  CLASS DÀNH CHO QUÂN — ImageSender
#  Quân tích hợp vào ChatServer để broadcast/unicast ảnh
# ─────────────────────────────────────────────────────────────

class ImageSender:
    """
    Wrapper tiện lợi để Quân gửi ảnh từ Server.

    Ví dụ dùng trong ChatServer của Quân:
        sender = ImageSender()
        img_bytes = sender.capture_and_encode()
        if img_bytes:
            sender.send_to(client_socket, img_bytes)
    """

    def __init__(self, cam_index: int = 0, quality: int = 80):
        self.cam_index = cam_index
        self.quality = quality

    def capture_and_encode(self) -> Optional[bytes]:
        """Chụp webcam và encode thành bytes sẵn gửi."""
        img_bytes, _ = frame_to_bytes_pipeline(self.cam_index, ".jpg", self.quality)
        return img_bytes

    @staticmethod
    def send_to(sock: socket.socket, img_bytes: bytes) -> bool:
        """Gửi bytes ảnh đến một socket Client cụ thể."""
        return send_image(sock, img_bytes)

    @staticmethod
    def broadcast(client_sockets: list, img_bytes: bytes) -> int:
        """
        Gửi ảnh đến nhiều Client cùng lúc.
        Returns: số Client nhận thành công.
        """
        ok = 0
        for sock in client_sockets:
            if send_image(sock, img_bytes):
                ok += 1
        return ok


# ─────────────────────────────────────────────────────────────
#  CLASS DÀNH CHO QUỲNH ANH — ImageReceiver
#  Quỳnh Anh chạy trong QThread, nhận ảnh và emit Signal
# ─────────────────────────────────────────────────────────────

class ImageReceiver:
    """
    Wrapper nhận ảnh liên tục, dùng trong QThread của Quỳnh Anh.

    Ví dụ tích hợp PySide6 (Quỳnh Anh):
    ─────────────────────────────────────
    class ReceiverThread(QThread):
        image_received = Signal(np.ndarray)

        def __init__(self, sock):
            super().__init__()
            self.receiver = ImageReceiver(sock, callback=self.image_received.emit)

        def run(self):
            self.receiver.start_loop()

    # Trong MainWindow:
    thread = ReceiverThread(client_sock)
    thread.image_received.connect(self.update_image_label)
    thread.start()
    ─────────────────────────────────────
    """

    def __init__(self, sock: socket.socket, callback: Callable[[np.ndarray], None]):
        """
        Args:
            sock    : socket kết nối đến Server
            callback: Hàm gọi khi nhận được frame mới (ví dụ: emit Signal)
        """
        self.sock = sock
        self.callback = callback
        self._running = False

    def start_loop(self):
        """Vòng lặp nhận ảnh liên tục. Chạy trong QThread."""
        self._running = True
        while self._running:
            frame = receive_image(self.sock)
            if frame is None:
                print("[ImageReceiver] Kết nối đứt hoặc không còn ảnh.")
                break
            self.callback(frame)   # Emit signal lên UI thread

    def stop(self):
        """Dừng vòng lặp (gọi từ main thread khi đóng app)."""
        self._running = False


# ─────────────────────────────────────────────────────────────
#  CLASS DÀNH CHO QUỲNH ANH — MessageSearchEngine
#  Tích hợp vào thanh tìm kiếm trên UI
# ─────────────────────────────────────────────────────────────

class MessageSearchEngine:
    """
    Engine tìm kiếm tin nhắn cục bộ cho UI của Quỳnh Anh.

    Ví dụ tích hợp PySide6:
    ─────────────────────────────────────
    engine = MessageSearchEngine()

    # Mỗi khi nhận tin nhắn mới:
    engine.add_message(Message(id, sender, content, timestamp, room))

    # Khi người dùng nhập vào QLineEdit và bấm Enter:
    results = engine.search(keyword)
    for r in results:
        browser.append(r.highlighted_content)
    ─────────────────────────────────────
    """

    def __init__(self):
        self._messages: List[Message] = []

    def add_message(self, msg: Message):
        """Thêm tin nhắn mới vào bộ nhớ cục bộ."""
        self._messages.append(msg)

    def add_messages_bulk(self, msgs: List[Message]):
        """Thêm nhiều tin nhắn cùng lúc (khi load lịch sử)."""
        self._messages.extend(msgs)

    def clear(self):
        """Xóa toàn bộ lịch sử (khi đổi phòng/nhóm)."""
        self._messages.clear()

    def search(self, keyword: str, case_sensitive: bool = False) -> List[SearchResult]:
        """Tìm kiếm và trả về kết quả có highlighted content."""
        return search_messages(self._messages, keyword, case_sensitive)

    def get_qt_html_results(self, keyword: str) -> List[str]:
        """
        Trả về list HTML string sẵn dùng với QTextBrowser.setHtml().
        """
        results = self.search(keyword)
        html_list = []
        for r in results:
            html = highlight_for_qt(r.message.content, r.match_positions)
            line = (
                f'<b style="color:#555">[{r.message.timestamp}] '
                f'{r.message.sender}:</b> {html}'
            )
            html_list.append(line)
        return html_list

    @property
    def total_messages(self) -> int:
        return len(self._messages)


# ─────────────────────────────────────────────────────────────
#  DEMO TÍCH HỢP
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print(" INTEGRATION MODULE — API cho Quân & Quỳnh Anh")
    print("=" * 55)

    # Demo MessageSearchEngine (Quỳnh Anh)
    engine = MessageSearchEngine()
    engine.add_messages_bulk([
        Message(1, "Quân",     "Server khởi động thành công",    "08:00"),
        Message(2, "Tiến",     "Test gửi ảnh, kích thước 45KB",  "08:05"),
        Message(3, "QuỳnhAnh", "UI hiển thị ảnh ok rồi!",        "08:06"),
        Message(4, "Quân",     "Merge PR vào main nhé mọi người", "08:10"),
        Message(5, "Tiến",     "Stress test 50 client xong",      "08:15"),
    ])

    print(f"\n[Engine] Tổng tin nhắn: {engine.total_messages}")
    html_results = engine.get_qt_html_results("test")
    print(f"[Engine] Tìm 'test': {len(html_results)} kết quả")
    for html in html_results:
        print(f"  {html}")

    # Demo ImageSender (Quân)
    print(f"\n[ImageSender] Broadcast API sẵn sàng — Quân tích hợp vào ChatServer")

    # Demo ImageReceiver (Quỳnh Anh)
    print(f"[ImageReceiver] Receiver API sẵn sàng — Quỳnh Anh tích hợp vào QThread")

    print("\n[DONE] Module tích hợp OK.")
