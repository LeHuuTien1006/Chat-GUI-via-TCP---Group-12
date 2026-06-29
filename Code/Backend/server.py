import socket
import threading
import json
import struct

HOST = '127.0.0.1'
PORT = 9999

# Đổi cấu trúc lưu trữ từ địa chỉ IP sang nickname (Client ID)
clients = {} # Định dạng: {"nickname": conn}
groups = {}  # Định dạng: {"group_id": {"admin": "nickname", "members": ["nick1", "nick2"]}}

def recv_exact(conn, size):
    data = b""
    while len(data) < size:
        packet = conn.recv(size - len(data))
        if not packet: 
            return None
        data += packet
    return data

def handle_client(conn, addr):
    print(f"[+] Co ket noi vat ly tu: {addr}")
    current_nickname = None
    
    while True:
        try:
            # 1. Luôn nhận 4 byte header trước
            header = recv_exact(conn, 4)
            if not header: break
            size = struct.unpack("!I", header)[0]
            
            # TỐI ƯU BỘ ĐỆM (CHỐNG TRÀN RAM)
            # Nếu file lớn hơn 500KB (512000 bytes) -> Stream (chia nhỏ)
            if size > 512000: 
                print(f"[{current_nickname}] Dang stream file lon ({size} bytes) de chong tran RAM...")
                img_header = struct.pack("!I", size)
                
                # Bắn header cho các client khác trước
                for nick, c_conn in list(clients.items()):
                    if nick != current_nickname:
                        try: c_conn.sendall(img_header)
                        except: pass
                
                # Bắt đầu nhận và xả thẳng vào các socket đích (Chunking 4KB/lần)
                bytes_received = 0
                while bytes_received < size:
                    chunk_size = min(4096, size - bytes_received)
                    chunk = conn.recv(chunk_size)
                    if not chunk: break
                    
                    for nick, c_conn in list(clients.items()):
                        if nick != current_nickname:
                            try: c_conn.sendall(chunk)
                            except: pass
                    bytes_received += len(chunk)
                    
                continue # Xong luồng stream, quay lại chờ gói tin mới

            # Nhận payload bình thường cho gói tin nhỏ (Chat hoặc Ảnh nhẹ)
            payload = recv_exact(conn, size)
            if not payload: break
            
            try:
                # Thử giải mã JSON
                text = payload.decode('utf-8')
                data_json = json.loads(text)
                msg_type = data_json.get("type")
                
                # LOGIN & QUẢN LÝ CLIENT ID
                if msg_type == "login":
                    nickname = data_json.get("nickname")
                    if nickname in clients:
                        # Chặn trùng tên
                        reply = json.dumps({"type": "error", "msg": "Ten da ton tai!"}).encode('utf-8')
                        conn.sendall(struct.pack("!I", len(reply)) + reply)
                    else:
                        current_nickname = nickname
                        clients[nickname] = conn
                        print(f"[*] {nickname} da dang nhap thanh cong.")
                        reply = json.dumps({"type": "info", "msg": "OK"}).encode('utf-8')
                        conn.sendall(struct.pack("!I", len(reply)) + reply)
                        
                # TÍNH NĂNG GỐC: CHAT TOÀN SERVER (BROADCAST)
                elif msg_type == "chat_all":
                    sender = data_json.get("sender")
                    content = data_json.get("content")
                    forward_msg = json.dumps({"type": "new_message", "sender": sender, "content": content}).encode('utf-8')
                    forward_header = struct.pack("!I", len(forward_msg))
                    for nick, c_conn in list(clients.items()):
                        if nick != current_nickname:
                            try: c_conn.sendall(forward_header + forward_msg)
                            except: pass
                            
                # NHẮN TIN RIÊNG 1-1 (UNICAST)
                elif msg_type == "chat_private":
                    sender = data_json.get("sender")
                    receiver = data_json.get("receiver")
                    content = data_json.get("content")
                    if receiver in clients:
                        forward_msg = json.dumps({"type": "private_message", "sender": sender, "content": content}).encode('utf-8')
                        try:
                            clients[receiver].sendall(struct.pack("!I", len(forward_msg)) + forward_msg)
                        except: pass
                        
                # NHÓM CHAT (MULTICAST)
                elif msg_type == "create_group":
                    group_id = data_json.get("group_id")
                    if group_id not in groups:
                        groups[group_id] = {"admin": current_nickname, "members": [current_nickname]}
                        print(f"[*] {current_nickname} da tao nhom: {group_id}")
                        
                elif msg_type == "join_group":
                    group_id = data_json.get("group_id")
                    if group_id in groups and current_nickname not in groups[group_id]["members"]:
                        groups[group_id]["members"].append(current_nickname)
                        print(f"[*] {current_nickname} da vao nhom: {group_id}")
                        
                elif msg_type == "chat_group":
                    group_id = data_json.get("group_id")
                    sender = data_json.get("sender")
                    content = data_json.get("content")
                    if group_id in groups and sender in groups[group_id]["members"]:
                        forward_msg = json.dumps({"type": "group_message", "group_id": group_id, "sender": sender, "content": content}).encode('utf-8')
                        forward_header = struct.pack("!I", len(forward_msg))
                        for mem in groups[group_id]["members"]:
                            if mem != sender and mem in clients:
                                try: clients[mem].sendall(forward_header + forward_msg)
                                except: pass

            except UnicodeDecodeError:
                # Xử lý ảnh kích thước nhỏ gọn (dưới 500KB)
                print(f"[{current_nickname}] Nhan file ANH nho ({size} bytes).")
                img_header = struct.pack("!I", len(payload))
                for nick, c_conn in list(clients.items()):
                    if nick != current_nickname:
                        try: c_conn.sendall(img_header + payload)
                        except: pass

        except Exception as e:
            break

    # Dọn dẹp RAM & Danh sách khi Client thoát
    if current_nickname and current_nickname in clients:
        del clients[current_nickname]
        print(f"[-] {current_nickname} da ngat ket noi.")
        
    # Tự động xóa người dùng khỏi các nhóm
    for g_id, g_data in groups.items():
        if current_nickname in g_data["members"]:
            g_data["members"].remove(current_nickname)
            
    conn.close()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"Server UDM_08 dang chay tai {HOST}:{PORT}...")
    while True:
        conn, addr = s.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.start()

if __name__ == "__main__":
    main()
