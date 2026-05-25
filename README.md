# [cite_start]PROJECT CODE: UDM_08 Lập trình ứng dụng Chat (GUI) via TCP [cite: 86]

## [cite_start]1. Mục tiêu dự án [cite: 89]
[cite_start]Dự án phát triển một Ứng dụng Chat nâng cao theo mô hình Client-Server, sử dụng giao thức TCP/IP thông qua thư viện socket của Python để đảm bảo truyền tải dữ liệu (tin nhắn, tệp tin, lệnh điều hướng hệ thống) một cách tin cậy, toàn vẹn và đúng thứ tự[cite: 90]. 

[cite_start]Ứng dụng được xây dựng giao diện đồ họa (Desktop GUI) hoàn chỉnh bằng PySide6, đáp ứng đầy đủ tiêu chí không sử dụng ứng dụng dòng lệnh (Console) hay ứng dụng Web (Webapp)[cite: 91].

## [cite_start]2. Thành viên nhóm [cite: 87]

| STT | Họ và tên | MSSV | Tài khoản Github |
|---|---|---|---|
| 1 | Đỗ Nguyễn Quỳnh Anh | 086306005322 | [cite_start][QynhAnhh](https://github.com/QynhAnhh) | [cite: 88]
| 2 | Trần Minh Quân | 352774521 | [cite_start][quantran9739-png](https://github.com/quantran9739-png) | [cite: 88]
| 3 | Lê Hữu Tiến | 072206006554 | [cite_start][tiendz126](https://github.com/tiendz126) | [cite: 88]

## [cite_start]3. Các tính năng chính [cite: 92]

### Hệ thống mạng & Kết nối
* [cite_start]**Kết nối đa luồng (Concurrent Connection):** Server sử dụng đa luồng để quản lý đồng thời nhiều Client[cite: 93]. [cite_start]Client sử dụng QThread của PySide6 để nhận dữ liệu từ mạng mà không gây treo (freeze) giao diện[cite: 94].

### [cite_start]Hệ thống Chat & Quản lý Nhóm [cite: 96]
* [cite_start]**Chat cốt lõi:** Hỗ trợ chat phòng chung mặc định (Broadcast) và nhắn tin riêng tư 1-1 (Unicast)[cite: 95].
* [cite_start]**Tạo nhóm chat mới (Create Group Chat):** Người dùng có thể chọn nhiều thành viên từ danh sách online để tạo phòng chat nhóm (Multicast)[cite: 97]. [cite_start]Người tạo nhóm ban đầu sẽ tự động trở thành Nhóm trưởng (Admin)[cite: 98].
* [cite_start]**Quyền hạn của Nhóm trưởng (Kick Member):** Nhóm trưởng có menu giao diện riêng (chuột phải vào thành viên) để thực hiện lệnh xóa (kích) bất kỳ thành viên nào ra khỏi nhóm[cite: 99]. [cite_start]Server sẽ gửi gói tin buộc Client bị kích phải đóng phòng chat và xóa họ khỏi danh sách nhận tin[cite: 100].
* [cite_start]**Rời nhóm và chuyển giao quyền lực:** Thành viên thông thường có thể tự động rời nhóm[cite: 101]. [cite_start]Nếu Nhóm trưởng chủ động rời nhóm, hệ thống Server sẽ tự động chọn ngẫu nhiên một thành viên bất kỳ còn lại trong nhóm để chuyển giao quyền Nhóm trưởng (Admin mới) nhằm duy trì hoạt động nhóm[cite: 102].

### Cá nhân hóa & Tiện ích
* [cite_start]**Đặt biệt danh (Nickname Customization):** Người dùng có thể thay đổi biệt danh hiển thị của mình trong phòng chat[cite: 103].
* [cite_start]**Đổi màu nền (Chat Theme):** Tùy biến màu sắc nền hoặc chủ đề của giao diện hộp thoại theo sở thích[cite: 104].
* [cite_start]**Tìm kiếm tin nhắn (Message Search):** Lọc và tìm kiếm lại các tin nhắn cũ trong lịch sử cuộc trò chuyện dựa trên từ khóa[cite: 105].
* [cite_start]**Tắt/Bật thông báo (Mute/Unmute Notifications):** Tùy chọn tắt âm thanh hoặc thông báo đẩy đối với các nhóm chat hoặc người dùng cụ thể[cite: 106].
* [cite_start]**Chặn người dùng (Block Users):** Tính năng cho phép chặn tin nhắn riêng tư từ một người dùng khác[cite: 107].

### Đa phương tiện
* [cite_start]**Gửi Sticker (Nhãn dán):** Tích hợp sẵn bộ sticker sinh động, truyền tải qua mã định danh giữa các Client[cite: 108].
* [cite_start]**Chụp ảnh từ Camera:** Tích hợp tính năng gọi camera máy tính bằng OpenCV, cho phép chụp ảnh trực tiếp và gửi ngay qua luồng dữ liệu byte của TCP[cite: 109].

## [cite_start]4. Công nghệ (Tech Stack) [cite: 110]
* [cite_start]**Kiến trúc:** Mô hình Client-Server độc lập[cite: 111].
* [cite_start]**Giao thức mạng:** TCP/IP (socket và struct trong thư viện tiêu chuẩn Python)[cite: 112].
* [cite_start]**Ngôn ngữ lập trình:** Python[cite: 113].
* [cite_start]**Khung giao diện (GUI Framework):** PySide6 (Sử dụng các widget như QListWidget, QTextBrowser, QDialog, QMenu,...)[cite: 114].
* [cite_start]**Xử lý đa luồng & GUI:** QThread và hệ thống Signal/Slot của PySide6[cite: 115].
* [cite_start]**Xử lý Camera:** Thư viện opencv-python (cv2)[cite: 116].
* [cite_start]**Đóng gói dữ liệu:** Định dạng JSON (cho tin nhắn, gói lệnh hệ thống) kết hợp với Header nhị phân (cho dữ liệu thô của ảnh camera)[cite: 117].

## [cite_start]5. Kết quả đạt được (Final Output) [cite: 118]
[cite_start]Sản phẩm cuối cùng là phần mềm Desktop hoàn chỉnh, xử lý mượt mà các kịch bản mạng phức tạp liên quan đến quyền sở hữu nhóm chat[cite: 119, 120]. Ứng dụng bao gồm:
* [cite_start]**ChatServer:** Xử lý điều hướng tin nhắn, quản lý ID nhóm, cập nhật trạng thái Admin khi nhóm trưởng rời nhóm hoặc kích người[cite: 119].
* [cite_start]**ChatClient:** Giao diện PySide6 cho phép người dùng chat, quản lý nhóm nếu là Admin, chụp ảnh camera[cite: 119].
