"""
Task 2.1 + 2.2 - Mở Camera & Encode Ảnh
Nhóm 12 - Lê Hữu Tiến
Tích hợp opencv-python: mở webcam, chụp frame, encode thành byte array.
"""

import cv2
import numpy as np
from typing import Optional, Tuple


# ─────────────────────────────────────────────────────────────
#  TASK 2.1 — MỞ CAMERA & CHỤP FRAME
# ─────────────────────────────────────────────────────────────

def open_camera(cam_index: int = 0) -> Optional[cv2.VideoCapture]:
    """
    Mở webcam.

    Args:
        cam_index: 0 = webcam mặc định, 1 = camera ngoài, ...

    Returns:
        VideoCapture object nếu mở thành công, None nếu thất bại.
    """
    cap = cv2.VideoCapture(cam_index)
    if not cap.isOpened():
        print(f"[CAMERA] ✗ Không mở được camera index={cam_index}")
        return None
    print(f"[CAMERA] ✓ Mở camera index={cam_index} thành công")
    print(f"[CAMERA]   Độ phân giải: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
          f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print(f"[CAMERA]   FPS: {cap.get(cv2.CAP_PROP_FPS)}")
    return cap


def capture_frame(cap: cv2.VideoCapture) -> Optional[np.ndarray]:
    """
    Chụp một frame từ VideoCapture.

    Returns:
        numpy ndarray (H, W, 3) BGR nếu thành công, None nếu thất bại.
    """
    ret, frame = cap.read()
    if not ret or frame is None:
        print("[CAMERA] ✗ Không đọc được frame")
        return None
    h, w = frame.shape[:2]
    print(f"[CAMERA] ✓ Chụp frame: {w}x{h} px, dtype={frame.dtype}")
    return frame


def release_camera(cap: cv2.VideoCapture) -> None:
    """Đóng camera, giải phóng tài nguyên."""
    cap.release()
    print("[CAMERA] Camera đã đóng.")


# ─────────────────────────────────────────────────────────────
#  TASK 2.2 — ENCODE ẢNH THÀNH BYTE ARRAY
# ─────────────────────────────────────────────────────────────

def encode_frame_to_bytes(
    frame: np.ndarray,
    format: str = ".jpg",
    quality: int = 80
) -> Optional[bytes]:
    """
    Chuyển ma trận ảnh OpenCV thành mảng byte để gửi qua socket.

    Args:
        frame  : numpy array BGR từ cv2.VideoCapture
        format : ".jpg" (nhanh, nhỏ) hoặc ".png" (lossless, lớn hơn)
        quality: JPEG quality 0-100 (chỉ dùng khi format=".jpg")

    Returns:
        bytes nếu thành công, None nếu thất bại.
    """
    if format == ".jpg":
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    elif format == ".png":
        encode_params = [cv2.IMWRITE_PNG_COMPRESSION, 3]   # 0=no compress, 9=max
    else:
        encode_params = []

    success, buffer = cv2.imencode(format, frame, encode_params)
    if not success:
        print(f"[ENCODE] ✗ imencode thất bại với format={format}")
        return None

    img_bytes = buffer.tobytes()
    print(f"[ENCODE] ✓ Encode thành công: format={format}, "
          f"size={len(img_bytes):,} byte ({len(img_bytes)/1024:.1f} KB)")
    return img_bytes


def decode_bytes_to_frame(img_bytes: bytes) -> Optional[np.ndarray]:
    """
    Giải mã byte array về lại numpy array (dùng bên nhận).

    Args:
        img_bytes: Bytes nhận từ socket (sau khi gom đủ theo Header)

    Returns:
        numpy ndarray BGR nếu thành công, None nếu thất bại.
    """
    buffer = np.frombuffer(img_bytes, dtype=np.uint8)
    frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if frame is None:
        print("[DECODE] ✗ imdecode thất bại — data bị hỏng?")
        return None
    h, w = frame.shape[:2]
    print(f"[DECODE] ✓ Decode thành công: {w}x{h} px")
    return frame


# ─────────────────────────────────────────────────────────────
#  HÀM TIỆN ÍCH GHÉP NỐI VỚI QUỲNH ANH
# ─────────────────────────────────────────────────────────────

def frame_to_bytes_pipeline(
    cam_index: int = 0,
    format: str = ".jpg",
    quality: int = 80
) -> Tuple[Optional[bytes], Optional[np.ndarray]]:
    """
    Pipeline hoàn chỉnh: mở cam → chụp → encode → trả về bytes.
    Quân sẽ gọi hàm này để lấy bytes gửi qua socket.

    Returns:
        (img_bytes, original_frame) — cả hai có thể là None nếu lỗi.
    """
    cap = open_camera(cam_index)
    if cap is None:
        return None, None

    frame = capture_frame(cap)
    release_camera(cap)

    if frame is None:
        return None, frame

    img_bytes = encode_frame_to_bytes(frame, format, quality)
    return img_bytes, frame


# ─────────────────────────────────────────────────────────────
#  TEST THỦ CÔNG (dùng ảnh giả nếu không có webcam)
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print(" TASK 2.1 + 2.2 — CAMERA & ENCODE TEST")
    print("=" * 55)

    # Tạo ảnh giả 640x480 màu ngẫu nhiên (dùng khi không có webcam)
    fake_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    cv2.putText(fake_frame, "Group12 - UDM_08", (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
    print("\n[TEST] Dùng ảnh giả 640x480 (thay cho webcam)")

    # Test encode JPEG
    print("\n--- Encode JPEG (quality=80) ---")
    jpg_bytes = encode_frame_to_bytes(fake_frame, ".jpg", quality=80)

    # Test encode PNG
    print("\n--- Encode PNG ---")
    png_bytes = encode_frame_to_bytes(fake_frame, ".png")

    # Test round-trip: encode → decode
    if jpg_bytes:
        print("\n--- Round-trip: encode → decode ---")
        recovered = decode_bytes_to_frame(jpg_bytes)
        if recovered is not None:
            print(f"[TEST] ✓ Round-trip thành công: {recovered.shape}")

    # So sánh kích thước
    if jpg_bytes and png_bytes:
        print(f"\n--- So sánh kích thước ---")
        print(f"  JPEG (q=80) : {len(jpg_bytes):>8,} byte  ({len(jpg_bytes)/1024:>7.1f} KB)")
        print(f"  PNG         : {len(png_bytes):>8,} byte  ({len(png_bytes)/1024:>7.1f} KB)")
        ratio = len(png_bytes) / len(jpg_bytes)
        print(f"  PNG lớn hơn JPEG {ratio:.1f}x → Dùng JPEG cho realtime chat ✓")

    print("\n[DONE] Task 2.1 + 2.2 hoàn thành.")
