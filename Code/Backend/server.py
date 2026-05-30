import socket
import threading

# Cấu hình IP và Port cục bộ để test
HOST = '127.0.0.1'
PORT = 9999

# Danh sách lưu các client đang online
# Cấu trúc: {địa_chỉ_ip: biến_socket_của_client}
clients = {}

def handle_client(conn, addr):
    # Hàm này chạy riêng cho mỗi client kết nối vào
    print("-> Co nguoi moi ket noi: ", addr)
    
    while True:
        try:
            # Nhận tin nhắn từ client (tối đa 1024 byte)
            data = conn.recv(1024)
            
            # Nếu không nhận được data tức là client tự ngắt kết nối
            if not data:
                print("<- Client da thoat: ", addr)
                break
                
            # Đọc tin nhắn và in ra màn hình console của Server
            message = data.decode('utf-8')
            print("Tin nhan tu", addr, "la:", message)
            
            # Gửi tin nhắn test phản hồi lại cho Client đó
            reply = "Server da nhan duoc tin nha!"
            conn.send(reply.encode('utf-8'))
            
        except:
            # Lỗi mạng hoặc client tắt app ngang thì thoát vòng lặp
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
        # Nếu không có thread, server sẽ bị treo, người thứ 2 không vào được
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.start()

# Chạy hàm main khi mở file
if __name__ == "__main__":
    main()
