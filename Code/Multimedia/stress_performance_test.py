"""
Stress Test & Performance Test
Nhóm 12 - Lê Hữu Tiến
────────────────────────────────────────────────────────────
Chụp ảnh màn hình minh chứng các bài test, lưu vào thư mục Extra.
Theo đặc tả: Quân chạy Server, Tiến và Quỳnh Anh bật nhiều cửa sổ
Client để test kick tài khoản, gửi ảnh xem hệ thống có bị sập không.
────────────────────────────────────────────────────────────
"""

import socket
import threading
import time
import struct
import numpy as np
import cv2
import os
import json
from dataclasses import dataclass, field
from typing import List, Dict


# ─────────────────────────────────────────────────────────────
#  CẤU TRÚC KẾT QUẢ TEST
# ─────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    test_name: str
    total_clients: int
    success_count: int
    fail_count: int
    duration_sec: float
    images_sent: int = 0
    avg_latency_ms: float = 0.0
    notes: str = ""

    @property
    def success_rate(self) -> float:
        if self.total_clients == 0:
            return 0.0
        return self.success_count / self.total_clients * 100


def _make_fake_frame(text: str = "Test") -> bytes:
    """Tạo ảnh giả và encode thành JPEG bytes."""
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[:] = (30, 60, 90)
    cv2.putText(frame, text, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()


def _send_with_header(sock: socket.socket, img_bytes: bytes):
    """Gửi ảnh có 4-byte header (dùng cho test)."""
    header = struct.pack("!I", len(img_bytes))
    sock.sendall(header + img_bytes)


# ─────────────────────────────────────────────────────────────
#  STRESS TEST — ÉP TẢI SERVER
# ─────────────────────────────────────────────────────────────

def stress_test(
    server_host: str = "127.0.0.1",
    server_port: int = 9999,
    num_clients: int = 50,
    images_per_client: int = 10,
    timeout_sec: float = 5.0
) -> TestResult:
    """
    Tạo num_clients threads, mỗi thread kết nối Server và gửi ảnh.
    Đo số kết nối thành công / thất bại, tổng ảnh gửi được.

    Args:
        num_clients     : Số Client đồng thời (mặc định 50 theo yêu cầu)
        images_per_client: Mỗi Client gửi bao nhiêu ảnh
    """
    print(f"\n{'═'*55}")
    print(f" STRESS TEST: {num_clients} clients × {images_per_client} ảnh/client")
    print(f"{'═'*55}")

    img_bytes = _make_fake_frame("STRESS")
    results = {"success": 0, "fail": 0, "images": 0}
    lock = threading.Lock()
    latencies = []

    def client_worker(client_id: int):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_sec)
            sock.connect((server_host, server_port))

            for _ in range(images_per_client):
                t0 = time.perf_counter()
                _send_with_header(sock, img_bytes)
                dt = (time.perf_counter() - t0) * 1000

                with lock:
                    results["images"] += 1
                    latencies.append(dt)

            sock.close()
            with lock:
                results["success"] += 1
                if client_id % 10 == 0:
                    print(f"  [Client {client_id:>3}] ✓ Gửi {images_per_client} ảnh xong")

        except Exception as e:
            with lock:
                results["fail"] += 1
                print(f"  [Client {client_id:>3}] ✗ Lỗi: {type(e).__name__}")

    t_start = time.perf_counter()
    threads = [threading.Thread(target=client_worker, args=(i,), daemon=True)
               for i in range(num_clients)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=timeout_sec + 5)

    duration = time.perf_counter() - t_start
    avg_latency = sum(latencies) / len(latencies) if latencies else 0

    result = TestResult(
        test_name=f"Stress Test ({num_clients} clients)",
        total_clients=num_clients,
        success_count=results["success"],
        fail_count=results["fail"],
        duration_sec=round(duration, 2),
        images_sent=results["images"],
        avg_latency_ms=round(avg_latency, 2),
    )

    print(f"\n  Kết quả:")
    print(f"  ├─ Thành công  : {result.success_count}/{result.total_clients} ({result.success_rate:.1f}%)")
    print(f"  ├─ Thất bại    : {result.fail_count}")
    print(f"  ├─ Ảnh gửi được: {result.images_sent:,}")
    print(f"  ├─ Thời gian   : {result.duration_sec:.2f}s")
    print(f"  └─ Latency TB  : {result.avg_latency_ms:.2f}ms/ảnh")
    return result


# ─────────────────────────────────────────────────────────────
#  PERFORMANCE TEST — ĐO THÔNG LƯỢNG
# ─────────────────────────────────────────────────────────────

def performance_test(
    server_host: str = "127.0.0.1",
    server_port: int = 9999,
    duration_sec: int = 10,
    num_clients: int = 5
) -> TestResult:
    """
    Đo thông lượng (throughput): bao nhiêu ảnh/giây Server xử lý được
    với num_clients gửi liên tục trong duration_sec giây.
    """
    print(f"\n{'═'*55}")
    print(f" PERFORMANCE TEST: {num_clients} clients gửi liên tục {duration_sec}s")
    print(f"{'═'*55}")

    img_bytes = _make_fake_frame("PERF")
    counter = {"images": 0, "bytes": 0}
    lock = threading.Lock()
    stop_event = threading.Event()

    def sender(client_id: int):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((server_host, server_port))
            while not stop_event.is_set():
                _send_with_header(sock, img_bytes)
                with lock:
                    counter["images"] += 1
                    counter["bytes"] += len(img_bytes)
            sock.close()
        except Exception:
            pass

    threads = [threading.Thread(target=sender, args=(i,), daemon=True)
               for i in range(num_clients)]
    t_start = time.perf_counter()
    for t in threads:
        t.start()

    time.sleep(duration_sec)
    stop_event.set()
    for t in threads:
        t.join(timeout=3)

    elapsed = time.perf_counter() - t_start
    fps = counter["images"] / elapsed
    mbps = counter["bytes"] / elapsed / 1_048_576

    result = TestResult(
        test_name=f"Performance Test ({num_clients} clients, {duration_sec}s)",
        total_clients=num_clients,
        success_count=num_clients,
        fail_count=0,
        duration_sec=round(elapsed, 2),
        images_sent=counter["images"],
        notes=f"Throughput: {fps:.1f} fps | {mbps:.2f} MB/s"
    )

    print(f"\n  Kết quả:")
    print(f"  ├─ Tổng ảnh gửi: {counter['images']:,}")
    print(f"  ├─ Dữ liệu     : {counter['bytes']/1_048_576:.1f} MB")
    print(f"  ├─ Thời gian   : {elapsed:.2f}s")
    print(f"  ├─ Throughput  : {fps:.1f} fps")
    print(f"  └─ Băng thông  : {mbps:.2f} MB/s")
    return result


# ─────────────────────────────────────────────────────────────
#  LƯU KẾT QUẢ TEST DƯỚI DẠNG JSON (lưu vào Extra/)
# ─────────────────────────────────────────────────────────────

def save_test_results(results: List[TestResult], output_dir: str = "Extra"):
    """Lưu kết quả test thành JSON để gộp vào báo cáo DOCX."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(output_dir, f"test_results_{timestamp}.json")

    data = []
    for r in results:
        data.append({
            "test_name": r.test_name,
            "total_clients": r.total_clients,
            "success_count": r.success_count,
            "fail_count": r.fail_count,
            "success_rate_pct": round(r.success_rate, 1),
            "duration_sec": r.duration_sec,
            "images_sent": r.images_sent,
            "avg_latency_ms": r.avg_latency_ms,
            "notes": r.notes,
        })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n[SAVE] Kết quả lưu tại: {out_path}")
    return out_path


# ─────────────────────────────────────────────────────────────
#  MOCK SERVER ĐỂ TEST ĐỘC LẬP (không cần Quân chạy server thật)
# ─────────────────────────────────────────────────────────────

def _mock_server(host: str, port: int, stop_event: threading.Event):
    """Server giả để nhận và bỏ dữ liệu — dùng khi test độc lập."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(100)
    srv.settimeout(1.0)

    def handle(conn):
        try:
            while not stop_event.is_set():
                hdr = b""
                while len(hdr) < 4:
                    chunk = conn.recv(4 - len(hdr))
                    if not chunk:
                        return
                    hdr += chunk
                size = struct.unpack("!I", hdr)[0]
                received = 0
                while received < size:
                    chunk = conn.recv(min(4096, size - received))
                    if not chunk:
                        return
                    received += len(chunk)
        except Exception:
            pass
        finally:
            conn.close()

    while not stop_event.is_set():
        try:
            conn, _ = srv.accept()
            threading.Thread(target=handle, args=(conn,), daemon=True).start()
        except socket.timeout:
            continue
    srv.close()


if __name__ == "__main__":
    HOST, PORT = "127.0.0.1", 19999
    stop = threading.Event()

    # Khởi động mock server nền
    srv_thread = threading.Thread(target=_mock_server, args=(HOST, PORT, stop), daemon=True)
    srv_thread.start()
    time.sleep(0.3)

    all_results = []

    # 1. Stress test 30 clients
    r1 = stress_test(HOST, PORT, num_clients=30, images_per_client=5)
    all_results.append(r1)
    time.sleep(0.5)

    # 2. Performance test 5 clients trong 5 giây
    r2 = performance_test(HOST, PORT, duration_sec=5, num_clients=5)
    all_results.append(r2)

    # Lưu kết quả
    stop.set()
    save_test_results(all_results, output_dir="Extra")

    print(f"\n{'═'*55}")
    print(" TẤT CẢ TESTS HOÀN THÀNH — Tiến chụp màn hình lưu vào Extra/")
    print(f"{'═'*55}")
