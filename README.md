# PROJECT: UDM_08 Lập trình ứng dụng Chat (GUI) via TCP

## 1. Thành viên nhóm
| STT | Họ và tên | MSSV | Tài khoản GitHub |
|---|---|---|---|
| 1 | Đỗ Nguyễn Quỳnh Anh | 086306005322 | [QynhAnhh](https://github.com/QynhAnhh) |
| 2 | Trần Minh Quân | 352774521 | [quantran9739-png](https://github.com/quantran9739-png) |
| 3 | Lê Hữu Tiến | 072206006554 | [LeHuuTien1006](https://github.com/tiendz126) |

## 2. Công nghệ sử dụng
* **Ngôn ngữ:** Python
* **Giao thức mạng:** TCP/IP (thư viện socket, struct)
* **Giao diện (GUI):** PySide6
* **Đa luồng:** QThread và hệ thống Signal/Slot của PySide6
* **Xử lý Camera:** Thư viện opencv-python (cv2)
* **Đóng gói dữ liệu:** Định dạng JSON kết hợp Header nhị phân

## 3. Các tính năng chính
* **Kết nối đa luồng:** Server quản lý đồng thời nhiều Client; Client sử dụng QThread nhận dữ liệu mạng để tránh treo giao diện.
* **Hệ thống chat cốt lõi:** Hỗ trợ chat phòng chung (Broadcast) và nhắn tin riêng tư 1-1 (Unicast).
* **Quản lý nhóm chat:** Hỗ trợ tạo nhóm chat mới (Multicast) và tự động cấp quyền Admin cho người khởi tạo.
* **Quyền hạn Admin:** Menu chuột phải hỗ trợ kích thành viên ra khỏi nhóm; Server tự động gửi gói tin hệ thống ép Client bị kích phải đóng phòng chat.
* **Rời nhóm & Chuyển giao quyền:** Thành viên có thể tự động rời nhóm; nếu Admin rời nhóm, Server tự động chọn ngẫu nhiên một thành viên còn lại lên làm Admin mới để duy trì nhóm.
* **Cá nhân hóa & Tiện ích:** Thay đổi biệt danh hiển thị, tùy biến màu nền chat, tìm kiếm tin nhắn cũ bằng từ khóa, bật/tắt thông báo hội thoại, và chặn tin nhắn từ người dùng khác.
* **Đa phương tiện:** Gửi Sticker qua mã định danh và chụp ảnh trực tiếp từ Camera máy tính (OpenCV) gửi qua luồng byte TCP.

## 4. Kết quả đạt được (Final Output)
* **ChatServer:** Xử lý điều hướng tin nhắn, quản lý ID nhóm và tự động cập nhật trạng thái Admin.
* **ChatClient:** Giao diện đồ họa Desktop (PySide6) hỗ trợ người dùng chat, quản lý nhóm và gọi camera.
