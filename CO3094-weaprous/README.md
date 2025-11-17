# Ứng dụng HTTP Server & P2P Chat (CO3094)

Hệ thống được xây dựng theo kiến trúc Proxy Ngược (Reverse Proxy):
    Proxy Server: Chạy ở port 8080, là server trung gian.
    App Server: Chạy ở port 9000, xử lý toàn bộ logic nghiệp vụ (API).


## ✨ Tính năng chính
Task 2.1: HTTP Server (Web)
- Xác thực Stateful: Hỗ trợ đăng nhập (/login) và quản lý phiên (session) bằng cookie session_id.
- Kiểm soát Truy cập: Các trang được bảo vệ (/index.html) sẽ chuyển hướng về /401.html nếu chưa đăng nhập.
- Phục vụ File Tĩnh: Cung cấp các file như login.html, 401.html, 404.html.

Task 2.2: Hybrid P2P Chat (App)
- Client-Server: Dùng start_sampleapp.py làm Tracker Server ("Lobby") để đăng ký và tìm kiếm peer.
- Peer-to-Peer: Gửi tin nhắn chat (cả 1-1 và nhóm) trực tiếp giữa các client (peer) bằng socket.


## 🔧 Cài đặt
Dự án này yêu cầu Python 3 và một thư viện bên ngoài
- Kiểm tra phiên bản python:
```bash
python --version
```

- Cài đặt thư viện requests (dùng cho chat_ui.py):
```bash
pip install requests
```
hoặc 
```bash
python -m pip install requests
```

## 🏃 Hướng dẫn Chạy
    Để chạy toàn bộ hệ thống, bạn cần khởi động Server Stack (2 Terminal) và sau đó chạy Clients (Trình duyệt hoặc Chat App).

1. Khởi động Server Stack (Bắt buộc)
Bạn cần 2 Terminal chạy song song.

🖥️ Terminal 1: Chạy App Server 
```bash
python start_sampleapp.py --server-ip 127.0.0.1 --server-port 9000
```
Log: [Tracker] Da tai X users tu ... --- Tracker Server (Task 2.1 & 2.2) dang khoi dong tai 127.0.0.1:9000 ---

🖥️ Terminal 2: Chạy Proxy 
Lưu ý: Đảm bảo config/proxy.conf của bạn đã trỏ host "127.0.0.1:8080" đến proxy_pass http://127.0.0.1:9000;.

```bash
python start_proxy.py --server-ip 127.0.0.1 --server-port 8080
```
Log: [Proxy] Listening on IP 127.0.0.1 port 8080

2. Demo Task 2.1 (Web Login)
Mở Trình duyệt Web (khuyên dùng Ẩn danh).

- Truy cập http://127.0.0.1:8080/login.html (luôn dùng port 8080).
- Test 401:     truy cập http://127.0.0.1:8080/index.html khi chưa login -> 401.html.
        hoặc:   login sai tên tài khoản
- Test 404: nhập sai đường dẫn (vd: http://127.0.0.1:8080/hello)
- Test Login: Quay lại login.html, nhập user/pass (trong ./data/users.json)
- Sau khi login kiểm tra việc lưu lịch sử trang bằng việc truy cập: http://127.0.0.1:8080/index.html

3. Demo Task 2.2 (P2P Chat)

Mở Terminal 3 (Client A):
```bash
python chat_ui.py
```
- Một cửa sổ GUI popup sẽ hiện ra.
- Đăng nhập
- Cửa sổ chat chính của Khoa xuất hiện.

Mở Terminal 4 (Client B):

```bash
python chat_ui.py
```
- Một cửa sổ GUI popup thứ hai hiện ra.
- Đăng nhập với tài khoản khác
- Cửa sổ chat chính của Bob xuất hiện.

Test Chat Nhóm (Broadcast):
- Đặt 2 cửa sổ chat cạnh nhau.
- Tại cửa sổ của Khoa, (đảm bảo (group) chung được chọn), gõ "Hello Bob" và nhấn Send.
- Cửa sổ của Bob sẽ nhận được: [khoa]: Hello Bob.

Test Chat Riêng (Direct Message):
- Tại cửa sổ của Bob, nhấn "Reload Chat List".
- Click vào khoa trong danh bạ (Panel 1).
- Gõ "Hi Khoa, test DM" và nhấn Gửi.
- Cửa sổ của Khoa (Panel 1) sẽ hiển thị khoa (1). Click vào đó để đọc tin nhắn.

## 🏛️ Kiến trúc File
start_proxy.py: Reverse Proxy. Chuyển tiếp request.
start_sampleapp.py: App Server. Xử lý mọi API (Login, Chat, Session).
chat_ui.py: Client Chat (P2P). Ứng dụng GUI tkinter đa luồng.
daemon/: Thư mục "Động cơ".
    httpadapter.py: Bộ chuyển tiếp. Đọc request, gọi "hook" (nếu là API) hoặc phục vụ file tĩnh.
    request.py: Bộ phân tích. "Dịch" request thô thành object (.path, .body, .cookies).
    response.py: Bộ xây dựng. "Lắp ráp" response (cả API và File tĩnh, hỗ trợ cá nhân hóa).
    weaprous.py: Mini-framework, giúp "đăng ký" API route.
data/users.json: Database user.
www/: Chứa các file HTML tĩnh (Login, Index, 401, 404).