import socket
import threading
import json

# Cấu hình IP và Port cục bộ để test
HOST = '127.0.0.1'
PORT = 9999

# Danh sách lưu các client đang online
# Cấu trúc: {địa_chỉ_ip: biến_socket_của_client}
clients = {}

def handle_client(conn, addr):
    """
    Hàm này chạy riêng cho mỗi client kết nối vào để không làm treo Server.
    """
    print("-> Co nguoi moi ket noi tu: ", addr)
    
    while True:
        try:
            # Nhận dữ liệu từ client (tối đa 1024 byte cho các tin nhắn cơ bản)
            data = conn.recv(1024)
            
            # Nếu không nhận được data tức là client tự ngắt kết nối
            if not data:
                print("<- Client da thoat: ", addr)
                break
                
            # 1. Giải mã byte thành chuỗi thô
            raw_message = data.decode('utf-8')
            
            # 2. Chuyển chuỗi thô thành Dictionary (JSON)
            try:
                json_data = json.loads(raw_message)
            except json.JSONDecodeError:
                print("[-] Loi: Du lieu gui len khong phai JSON chuan, bo qua!")
                continue # Bỏ qua gói tin lỗi, chờ gói tiếp theo
            
            # 3. BỘ ĐỊNH TUYẾN (ROUTER): Kiểm tra xem Client muốn làm gì
            loai_tin_nhan = json_data.get("type")
            
            if loai_tin_nhan == "login":
                nickname = json_data.get("nickname")
                print(f"[LOGIN] {addr} vua dang nhap voi ten: {nickname}")
                
                # Gửi phản hồi chào mừng về cho client đó
                reply = {"type": "server_info", "message": f"Chao mung {nickname} gia nhap Server!"}
                conn.send(json.dumps(reply).encode('utf-8'))
                
            elif loai_tin_nhan == "chat_all":
                nguoi_gui = json_data.get("sender")
                noi_dung = json_data.get("content")
                print(f"[CHAT CHUNG] {nguoi_gui} noi: {noi_dung}")
                
                # Trả lời lại cho client test
                reply = {"type": "server_info", "message": f"Server da nhan tin nhan cua {nguoi_gui}"}
                conn.send(json.dumps(reply).encode('utf-8'))
                
            else:
                print("[?] Khong nhan dien duoc loai lenh nay:", loai_tin_nhan)
            
        except Exception as e:
            # Lỗi mạng hoặc client tắt app ngang thì thoát vòng lặp
            print("[-] Loi ket noi hoac ngat dot ngot:", e)
            break
            
    # Phần dọn dẹp khi client thoát (ra khỏi vòng lặp while)
    if addr in clients:
        del clients[addr] # Xóa khỏi danh sách online
    conn.close() # Đóng kết nối
    print("Da dong ket noi voi", addr)

def main():
    # 1. Tạo socket TCP
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 2. Bind IP và Port vào socket
    s.bind((HOST, PORT))
    
    # 3. Lắng nghe kết nối (cho phép tối đa 5 người đợi)
    s.listen(5) 
    print("=== SERVER DANG CHAY TAI IP", HOST, "PORT", PORT, "===")
    
    while True:
        # 4. Chờ client kết nối tới (code sẽ dừng ở đây chờ)
        conn, addr = s.accept()
        
        # Lưu client mới vào thư viện dictionary
        clients[addr] = conn
        print("Hien tai co", len(clients), "nguoi dang online.")
        
        # 5. Tạo một luồng (thread) riêng để xử lý client này
        # Việc này giúp nhiều người chat cùng lúc mà server không bị treo
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.start()

# Chạy hàm main khi mở file
if __name__ == "__main__":
    main()
