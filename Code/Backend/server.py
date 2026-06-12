import socket
import threading
import json
import struct

HOST = '127.0.0.1'
PORT = 9999
clients = {}

def recv_exact(conn, size):
    # Ham ho tro nhan du so byte, tranh loi dinh goi TCP
    data = b""
    while len(data) < size:
        packet = conn.recv(size - len(data))
        if not packet:
            return None
        data += packet
    return data

def handle_client(conn, addr):
    print("Co ket noi tu:", addr)
    
    while True:
        try:
            # 1. Nhan 4 byte header de lay size
            header = recv_exact(conn, 4)
            if not header:
                break
                
            size = struct.unpack("!I", header)[0]
            
            # 2. Nhan du lieu dua tren size
            payload = recv_exact(conn, size)
            if not payload:
                break
                
            # 3. Kiem tra xem la Text(JSON) hay la Anh(Binary)
            try:
                text = payload.decode('utf-8')
                data_json = json.loads(text)
                
                # Xu ly lenh Login
                if data_json.get("type") == "login":
                    name = data_json.get("nickname")
                    print(f"[{addr}] dang nhap: {name}")
                    
                    reply = json.dumps({"type": "info", "msg": "OK"}).encode('utf-8')
                    reply_header = struct.pack("!I", len(reply))
                    conn.sendall(reply_header + reply)
                    
                # Xu ly luong Chat chu (Broadcast)
                elif data_json.get("type") == "chat_all":
                    sender = data_json.get("sender")
                    content = data_json.get("content")
                    print(f"[{sender}] chat: {content}")
                    
                    forward_msg = json.dumps({"type": "new_message", "sender": sender, "content": content}).encode('utf-8')
                    forward_header = struct.pack("!I", len(forward_msg))
                    
                    # Vong lap chuyen tiep tin nhan cho cac client khac
                    for client_addr, client_conn in clients.items():
                        if client_addr != addr:
                            try:
                                client_conn.sendall(forward_header + forward_msg)
                            except:
                                pass
                        
            except UnicodeDecodeError:
                # Dich loi tieng Viet -> Day la luong byte anh cua Tien gui
                print(f"Nhan duoc file ANH tu {addr}, dung luong: {size} bytes")
                
                img_header = struct.pack("!I", len(payload))
                
                # Vong lap chuyen tiep anh cho cac client khac
                for client_addr, client_conn in clients.items():
                    if client_addr != addr:
                        try:
                            client_conn.sendall(img_header + payload)
                        except:
                            pass
                
        except Exception as e:
            print("Loi ngat ket noi:", e)
            break
            
    if addr in clients:
        del clients[addr]
    conn.close()
    print("Da dong ket noi:", addr)

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(5) 
    print(f"Server dang chay: {HOST}:{PORT}...")
    
    while True:
        conn, addr = s.accept()
        clients[addr] = conn
        print("So nguoi online:", len(clients))
        
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.start()

if __name__ == "__main__":
    main()
