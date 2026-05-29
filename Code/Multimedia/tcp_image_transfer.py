"""
Task 2.3 - Giải quyết TCP Sticky Packets (QUAN TRỌNG NHẤT)
Nhóm 12 - Lê Hữu Tiến
────────────────────────────────────────────────────────────
VẤN ĐỀ: TCP là stream protocol, không có ranh giới gói tin.
Khi gửi ảnh 50KB, bên nhận có thể nhận nhiều mảnh nhỏ
hoặc lẫn lộn với gói tin khác → ảnh bị hỏng.

GIẢI PHÁP: 4-byte Binary Header
  [4 byte = kích thước ảnh][...... N byte dữ liệu ảnh ......]
  Bên nhận đọc 4 byte → biết cần đọc thêm N byte → gom đủ.
────────────────────────────────────────────────────────────
"""

import struct
import socket
import threading
import time
import numpy as np
import cv2
from typing import Optional


# ─────────────────────────────────────────────────────────────
#  HÀM GỬI ẢNH (BÊN GỬI / CLIENT)
# ─────────────────────────────────────────────────────────────

def send_image(sock: socket.socket, img_bytes: bytes) -> bool:
    """
    Gửi ảnh qua TCP với 4-byte Binary Header.

    Cấu trúc gói:
        [4 byte: struct.pack("!I", len)] + [N byte: img_bytes]

    Args:
        sock      : socket đã kết nối đến Server (Quân)
        img_bytes : Bytes ảnh từ cv2.imencode

    Returns:
        True nếu gửi thành công, False nếu lỗi.
    """
    try:
        # Bước 1: Đo kích thước
        img_size = len(img_bytes)

        # Bước 2: Đóng gói kích thước vào 4 byte Header
        header = struct.pack("!I", img_size)

        # Bước 3: Nối Header + Data rồi gửi một lần (atomic)
        payload = header + img_bytes
        sock.sendall(payload)   # sendall đảm bảo gửi hết, không bị thiếu byte

        print(f"[SEND] ✓ Gửi: header={header.hex().upper()}, "
              f"data={img_size:,} byte, tổng={len(payload):,} byte")
        return True

    except (BrokenPipeError, ConnectionResetError, OSError) as e:
        print(f"[SEND] ✗ Lỗi gửi: {e}")
        return False


# ─────────────────────────────────────────────────────────────
#  HÀM NHẬN ẢNH (BÊN NHẬN / SERVER hoặc CLIENT)
# ─────────────────────────────────────────────────────────────

def recv_exact(sock: socket.socket, num_bytes: int) -> Optional[bytes]:
    """
    Vòng lặp recv() đảm bảo nhận đúng num_bytes byte.
    Đây là hàm cốt lõi giải quyết TCP sticky packets.

    Args:
        sock      : socket kết nối
        num_bytes : Số byte cần nhận chính xác

    Returns:
        bytes có đúng num_bytes byte, hoặc None nếu kết nối đứt.
    """
    data = b""
    while len(data) < num_bytes:
        remaining = num_bytes - len(data)
        chunk = sock.recv(min(remaining, 4096))   # Nhận tối đa 4KB mỗi lần
        if not chunk:
            print("[RECV] ✗ Kết nối bị đóng giữa chừng")
            return None
        data += chunk
    return data


def receive_image(sock: socket.socket) -> Optional[np.ndarray]:
    """
    Nhận ảnh từ socket và decode về numpy array.

    Quy trình:
        1. Nhận đúng 4 byte Header
        2. Giải mã Header → img_size
        3. Vòng lặp recv() cho đến khi gom đủ img_size byte
        4. cv2.imdecode → numpy array
        5. Trả về cho Quỳnh Anh hiển thị trên UI

    Returns:
        numpy ndarray BGR, hoặc None nếu lỗi.
    """
    # Bước 1: Nhận đúng 4 byte Header
    raw_header = recv_exact(sock, 4)
    if raw_header is None:
        return None

    # Bước 2: Dịch ra kích thước ảnh
    img_size = struct.unpack("!I", raw_header)[0]
    print(f"[RECV] Header nhận: {raw_header.hex().upper()} → img_size={img_size:,} byte")

    # Bước 3: Gom đủ img_size byte dữ liệu ảnh
    img_bytes = recv_exact(sock, img_size)
    if img_bytes is None:
        return None

    print(f"[RECV] ✓ Gom đủ {len(img_bytes):,} byte dữ liệu ảnh")

    # Bước 4: Giải mã bytes → numpy array
    buffer = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)

    if frame is None:
        print("[RECV] ✗ imdecode thất bại — data bị corrupt?")
        return None

    h, w = frame.shape[:2]
    print(f"[RECV] ✓ Decode thành công: {w}x{h} px → Đẩy lên UI Quỳnh Anh")
    return frame


# ─────────────────────────────────────────────────────────────
#  TEST NỘI BỘ: Mô phỏng Send/Receive qua socketpair
# ─────────────────────────────────────────────────────────────

def _sender_thread(send_sock: socket.socket, frames: list):
    """Thread giả lập Client gửi nhiều ảnh liên tiếp."""
    for i, frame in enumerate(frames):
        success, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if success:
            img_bytes = buf.tobytes()
            print(f"\n[SENDER] Gửi ảnh #{i+1}: {len(img_bytes):,} byte")
            send_image(send_sock, img_bytes)
            time.sleep(0.05)   # Nhỏ thôi để test sticky packets

    send_sock.close()
    print("\n[SENDER] Đã gửi hết, đóng socket.")


def run_loopback_test():
    """
    Test đầy đủ bằng socketpair (không cần mạng thật).
    Mô phỏng: Client gửi 5 ảnh, Server nhận và verify.
    """
    print("=" * 55)
    print(" TASK 2.3 — TCP STICKY PACKETS LOOPBACK TEST")
    print("=" * 55)

    # Tạo 5 ảnh giả kích thước khác nhau
    frames = [
        np.random.randint(0, 255, (480,  640, 3), dtype=np.uint8),   # ~30KB
        np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8),   # ~80KB
        np.random.randint(0, 255, (360,  640, 3), dtype=np.uint8),   # ~15KB
        np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8),  # ~200KB
        np.random.randint(0, 255, (240,  320, 3), dtype=np.uint8),   # ~7KB
    ]
    for i, f in enumerate(frames):
        cv2.putText(f, f"Frame #{i+1}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

    # socketpair: giả lập kênh TCP hai chiều
    client_sock, server_sock = socket.socketpair()

    # Sender chạy trong thread riêng
    t = threading.Thread(target=_sender_thread, args=(client_sock, frames), daemon=True)
    t.start()

    # Receiver chạy ở main thread
    received_ok = 0
    print("\n[RECEIVER] Bắt đầu nhận ảnh...\n")

    while True:
        try:
            frame = receive_image(server_sock)
            if frame is None:
                break
            received_ok += 1
            print(f"[RECEIVER] ✓ Ảnh #{received_ok} decode xong: {frame.shape[1]}x{frame.shape[0]}")
        except Exception as e:
            print(f"[RECEIVER] Kết thúc hoặc lỗi: {e}")
            break

    server_sock.close()
    t.join()

    print(f"\n{'─' * 55}")
    print(f"  KẾT QUẢ: Gửi {len(frames)} ảnh | Nhận thành công {received_ok} ảnh")
    status = "✓ PASS" if received_ok == len(frames) else "✗ FAIL"
    print(f"  {status} — Sticky packets đã được giải quyết bằng 4-byte Header")
    print(f"{'─' * 55}\n")


if __name__ == "__main__":
    run_loopback_test()
