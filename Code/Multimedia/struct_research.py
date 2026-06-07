"""
Task 1.2 - Nghiên cứu struct Python (Binary Header) 
Nhóm 12 - Lê Hữu Tiến
Script test nhỏ để hiểu cách đóng gói số nguyên thành 4 byte nhị phân,
chuẩn bị cho việc giải quyết TCP Sticky Packets ở Task 2.3.
"""

import struct


def demo_struct_basics():
    """Hiểu cách struct.pack / unpack hoạt động."""
    print("=" * 55)
    print(" TASK 1.2 — NGHIÊN CỨU struct (Binary Header)")
    print("=" * 55)

    # ── 1. Đóng gói số nguyên thành 4 byte ──────────────────
    size = 1024
    packed = struct.pack("!I", size)   # ! = Big-endian (network byte order), I = unsigned int 32-bit

    print(f"\n[1] Đóng gói số {size} thành 4 byte:")
    print(f"    struct.pack('!I', {size}) = {packed}")
    print(f"    Dạng hex : {packed.hex().upper()}")
    print(f"    Số byte  : {len(packed)} byte")

    # ── 2. Giải đóng gói (unpack) ──────────────────────────
    unpacked = struct.unpack("!I", packed)[0]
    print(f"\n[2] Giải đóng gói lại:")
    print(f"    struct.unpack('!I', {packed}) = ({unpacked},)")
    print(f"    Số nhận được: {unpacked}  ✓ Khớp với số gốc: {size == unpacked}")

    # ── 3. Các kích thước ảnh thực tế ──────────────────────
    test_sizes = [512, 4096, 65535, 102400, 1_048_576, 5_242_880]
    print(f"\n[3] Test với các kích thước ảnh thực tế:")
    print(f"    {'Kích thước':<15} {'Hex (4 byte)':<14} {'Unpack':<12} {'Khớp?'}")
    print(f"    {'─'*14} {'─'*13} {'─'*11} {'─'*6}")
    for s in test_sizes:
        p = struct.pack("!I", s)
        u = struct.unpack("!I", p)[0]
        label = f"{s:,}".replace(",", ".") + " B"
        print(f"    {label:<15} {p.hex().upper():<14} {u:<12,} {'✓' if u == s else '✗'}")

    # ── 4. Tại sao dùng Big-endian (!) ─────────────────────
    size_le = struct.pack("<I", 1024)   # Little-endian
    size_be = struct.pack(">I", 1024)   # Big-endian (= "!")
    print(f"\n[4] Big-endian vs Little-endian (kích thước = 1024):")
    print(f"    Little-endian '<I' : {size_le.hex().upper()} (PC-native, không ổn khi cross-platform)")
    print(f"    Big-endian    '>I' : {size_be.hex().upper()} (network byte order, chuẩn TCP/IP)")
    print(f"    => Luôn dùng '!I' (= '>I') để tránh lỗi khi Client/Server khác kiến trúc CPU.")

    # ── 5. Mô phỏng ghép Header + Data ─────────────────────
    print(f"\n[5] Mô phỏng ghép 4-byte Header vào đầu data:")
    fake_image_bytes = b"\xFF\xD8\xFF\xE0" + b"\x00" * 20   # JPEG magic bytes + padding
    header = struct.pack("!I", len(fake_image_bytes))
    full_payload = header + fake_image_bytes

    print(f"    Data gốc      : {len(fake_image_bytes)} byte")
    print(f"    Header 4 byte : {header.hex().upper()}")
    print(f"    Tổng gửi đi   : {len(full_payload)} byte (4 header + {len(fake_image_bytes)} data)")

    # ── 6. Mô phỏng bên nhận ───────────────────────────────
    print(f"\n[6] Mô phỏng bên nhận tách Header ra đọc kích thước:")
    received_header = full_payload[:4]           # Đọc đúng 4 byte đầu
    img_size = struct.unpack("!I", received_header)[0]
    received_data = full_payload[4:4 + img_size]  # Đọc đúng img_size byte tiếp theo

    print(f"    4 byte nhận đầu tiên : {received_header.hex().upper()}")
    print(f"    Giải ra kích thước   : {img_size} byte")
    print(f"    Đọc tiếp {img_size} byte data : {len(received_data)} byte nhận được")
    print(f"    Khớp với gốc? {'✓ YES' if received_data == fake_image_bytes else '✗ NO'}")

    print(f"\n{'=' * 55}")
    print(" KẾT LUẬN: struct.pack('!I', size) đóng gói size thành")
    print(" 4 byte big-endian. Bên nhận đọc 4 byte đầu, unpack ra")
    print(" size, rồi recv() đúng 'size' byte tiếp. → Giải TCP sticky.")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    demo_struct_basics()
