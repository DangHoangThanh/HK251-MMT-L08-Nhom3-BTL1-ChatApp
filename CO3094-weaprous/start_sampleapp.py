#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""

import json
import secrets
import socket
import argparse
import random
import string
import time
import threading 
from urllib.parse import parse_qs, unquote # Dùng để parse body
import os

from daemon.weaprous import WeApRous
PORT = 8000  # Port cho Tracker Server
HEARTBEAT_TIMEOUT = 30 # Xóa peer nếu không thấy "nhịp tim" trong 30 giây

app = WeApRous()

# =====================================================================
# KHỞI TẠO "DATABASE"
# =====================================================================

db_lock = threading.Lock()

USER_DB = {} 
ACTIVE_SESSIONS = {}
PEER_DB = {}
CHANNEL_DB = {
    "chung": [] 
}
OFFLINE_STORE = {}

# LOAD USER DATABASE
def load_user_db():
    """Đọc file users.json vào biến toàn cục USER_DB."""
    global USER_DB
    
    _APP_DIR = os.path.abspath(__file__)
    DB_PATH = os.path.join(os.path.dirname(_APP_DIR), 'data', 'users.json')
    
    try:
        with open(DB_PATH, "r") as f:
            with db_lock:
                USER_DB = json.load(f)
        print(f"[Tracker] Da tai {len(USER_DB)} users tu {DB_PATH}.")
    except Exception as e:
        print(f"[Tracker] KHONG THE TAI USER DB: {e}")

# =====================================================================
# HÀM TIỆN ÍCH (Utility Functions)
# =====================================================================

def extract_cookies(headers):
    """
    Extracts cookies from HTTP headers.

    :params headers (dict): Dictionary of HTTP headers.

    :rtype dict: Dictionary mapping cookie names to their values.
    """
    cookie_str = headers.get('cookie', '')
    cookies = {}
    if not cookie_str:
        return cookies
    for pair in cookie_str.split(';'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            cookies[key.strip()] = value.strip()
    return cookies

def get_user_from_session(headers):
    """
    Checks the 'session_id' cookie and returns the associated username if valid.

    :params headers (dict): Dictionary of HTTP headers.

    :rtype str or None: Returns the username if session is valid, otherwise None.
    """
    cookies = extract_cookies(headers)
    session_id = cookies.get("session_id")
    if not session_id:
        return None 

    with db_lock:
        # Look up the session ID in ACTIVE_SESSIONS
        username = ACTIVE_SESSIONS.get(session_id)
    
    return username 

def get_active_peers():
    """
    Retrieves active peers whose heartbeat was within the timeout threshold.

    Also removes peers that have timed out from the peer database and
    from all channels.

    :rtypes dict: Dictionary mapping active usernames to their peer info.
    """
    active_peers = {}
    current_time = int(time.time())
    
    with db_lock:
        # Copy to avoid modifying dict during iteration
        for username, data in PEER_DB.copy().items():
            if (current_time - data['last_seen']) < HEARTBEAT_TIMEOUT:
                active_peers[username] = data
            else:
                # Delete timed-out peer
                print(f"[Tracker] Xoa peer (timeout): {username}")
                del PEER_DB[username]
                # Delete from all channels
                for channel_users in CHANNEL_DB.values():
                    if username in channel_users:
                        channel_users.remove(username)
                        
    return active_peers

# =====================================================================
# API CHO TASK 2.1 (Login & Trang chủ)
# =====================================================================

@app.route('/login', methods=['POST'])
def login(headers, body):
    """
    Handle user login (Task 2.1A)

    :params headers (dict): HTTP request headers.
    :params body (str): HTTP request body.

    :rtype: (int, dict, dict) - Tuple of (status_code, response_body, response_headers)
    """
    try:
        parsed_body = parse_qs(body) 
        username = parsed_body.get('username', [''])[0]
        password = parsed_body.get('password', [''])[0]
    except Exception as e:
        return (400, {"status": "failed", "reason": "Bad request body"})

    # Xác thực với USER_DB
    with db_lock:
        expected_password = USER_DB.get(username)

    if expected_password and expected_password == password:
        # Create a new session
        print(f"[Tracker] Login thanh cong cho: {username}")
        session_id = secrets.token_hex(16) 
        
        # Store in ACTIVE_SESSIONS
        with db_lock:
            ACTIVE_SESSIONS[session_id] = username
            
        # Return tuple (status_code, body, headers)
            return (200, 
                {"__pass_through__": True, "username": username}, 
                {"Set-Cookie": f"session_id={session_id}; Path=/; HttpOnly"})
    else:
        print(f"[Tracker] Login that bai cho: {username}")
        return (401, {"login": "failed", "reason": "Invalid credentials"}, {})


@app.route('/index.html', methods=['GET'])
@app.route('/', methods=['GET'])
def get_index(headers, body):
    """
    Check session and return personalized index page (Task 2.1B)

    :params headers (dict): HTTP request headers.
    :params body (str): HTTP request body.

    :rtype: (int, dict) - Tuple of (status_code, response_body)
    """
    username = get_user_from_session(headers)
    if not username:
        # No session, return 401 Unauthorized
        return (401, {"status": "failed", "reason": "unauthorized"})
    
    # Valid session, return welcome message with username attached to request
    return {
        "__pass_through__": True,  # Signal to pass through
        "username": username       # Attach username
    }

# =====================================================================
# API CHO TASK 2.2 (Peer Registration & Discovery)
# =====================================================================

@app.route('/api/login', methods=['POST'])
def api_login(headers, body):
    """
    API Login CHỈ DÀNH CHO APP (Task 2.2).
    Nhận JSON, trả về JSON.
    """
    try:
        # App sẽ gửi JSON, không phải form-data
        data = json.loads(body) 
        username = data.get('username')
        password = data.get('password')
    except Exception as e:
        return (400, {"status": "failed", "reason": "Bad JSON request"})

    # Xác thực (giống hệt hàm login)
    with db_lock:
        expected_password = USER_DB.get(username)

    if expected_password and expected_password == password:
        print(f"[Tracker] API Login thanh cong cho: {username}")
        session_id = secrets.token_hex(16)
        with db_lock:
            ACTIVE_SESSIONS[session_id] = username
        return (200, 
                {"login": "success", "username": username}, 
                {"Set-Cookie": f"session_id={session_id}; Path=/; HttpOnly"})
    else:
        print(f"[Tracker] API Login that bai cho: {username}")
        return (401, {"login": "failed", "reason": "Invalid credentials"}, {})
    
    
@app.route('/register', methods=['POST'])
def register_peer(headers, body):
    """
    API for Chat Client (P2P) to register itself with the Tracker.

    :params headers (dict): HTTP request headers.
    :params body (str): HTTP request body.
    
    :rtype: (int, dict) - Tuple of (status_code, response_body)
    """
    # Authenticate user
    username = get_user_from_session(headers)
    if not username:
        return (401, {"status": "failed", "reason": "unauthorized"})

    # Extract peer info from body
    try:
        data = json.loads(body)
        peer_port = int(data.get("port"))
        peer_ip = "127.0.0.1"
    except Exception as e:
        return (400, {"status": "failed", "reason": f"Bad JSON body: {e}"})

    # Register peer in PEER_DB
    with db_lock:
        PEER_DB[username] = {
            "ip": peer_ip, 
            "port": peer_port, 
            "last_seen": int(time.time())
        }
        if username not in CHANNEL_DB["chung"]:
            CHANNEL_DB["chung"].append(username)
            
    print(f"[Tracker] Dang ky Peer: {username} tai {peer_ip}:{peer_port}")
    return (200, {"status": "registered", "peer": username})

@app.route('/heartbeat', methods=['GET'])
def heartbeat(headers, body):
    """
    API để Client Chat (P2P) báo "tôi vẫn sống".
    """
    username = get_user_from_session(headers)
    if not username:
        return (401, {"status": "failed", "reason": "unauthorized"})

    with db_lock:
        if username not in PEER_DB:
            return (404, {"status": "failed", "reason": "not registered"})
        PEER_DB[username]['last_seen'] = int(time.time())
        
    return (200, {"status": "ok"})

@app.route('/get-peers', methods=['GET'])
def get_peers(headers, body):
    """
    API để Client Chat (P2P) lấy danh sách peer (đã lọc).
    """
    username = get_user_from_session(headers)
    if not username:
        return (401, {"status": "failed", "reason": "unauthorized"})

    active_list = get_active_peers()
    return (200, active_list)

# =====================================================================
# API CHO TASK 2.2 (Channel Management)
# =====================================================================

@app.route('/api/send_offline', methods=['POST'])
def api_send_offline(headers, body):
    """
    Nhận tin nhắn từ User A gửi cho User B (khi B offline).
    Lưu vào OFFLINE_STORE.
    """
    username = get_user_from_session(headers) # Người gửi
    if not username: return (401, {"status": "failed"})
    
    try:
        data = json.loads(body)
        target_user = data.get("target_user")
        message_payload = data.get("payload") # Nội dung tin nhắn gốc
    except: return (400, {"status": "failed", "reason": "Bad JSON"})

    with db_lock:
        if target_user not in OFFLINE_STORE:
            OFFLINE_STORE[target_user] = []
        
        # Đánh dấu tin nhắn này là offline để Client nhận biết
        message_payload["is_offline"] = True
        message_payload["timestamp"] = time.time()
        
        OFFLINE_STORE[target_user].append(message_payload)
        
    print(f"[Tracker] Da luu tin nhan Offline cho: {target_user}")
    return (200, {"status": "saved"})

@app.route('/api/fetch_offline', methods=['GET'])
def api_fetch_offline(headers, body):
    """
    User B gọi API này để lấy tin nhắn đã bỏ lỡ.
    Sau khi lấy xong, Server sẽ XÓA tin nhắn đó (để không tải lại lần sau).
    """
    username = get_user_from_session(headers)
    if not username: return (401, {"status": "failed"})
    
    messages = []
    with db_lock:
        if username in OFFLINE_STORE:
            messages = OFFLINE_STORE[username]
            del OFFLINE_STORE[username] # Xóa sau khi đã lấy
            print(f"[Tracker] Tra {len(messages)} tin nhan offline cho {username}")
            
    return (200, {"status": "ok", "messages": messages})


@app.route('/channels/list', methods=['GET'])
def get_channel_list(headers, body):
    with db_lock: return (200, {"status": "ok", "channels": list(CHANNEL_DB.keys())})

@app.route('/channels/join', methods=['POST'])
def join_channel(headers, body):
    username = get_user_from_session(headers)
    try:
        channel = json.loads(body).get("channel_name")
        with db_lock:
            if channel not in CHANNEL_DB: CHANNEL_DB[channel] = []
            if username not in CHANNEL_DB[channel]: CHANNEL_DB[channel].append(username)
        return (200, {"status": "joined"})
    except: return (400, {"status": "error"})

@app.route('/channels/peers', methods=['POST'])
def get_channel_peers(headers, body):
    try:
        channel = json.loads(body).get("channel_name")
        actives = get_active_peers()
        with db_lock: users = CHANNEL_DB.get(channel, [])
        return (200, {u: actives[u] for u in users if u in actives})
    except: return (200, {})

# =====================================================================
# HÀM KHỞI ĐỘNG
# =====================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='TrackerServer', description='Backend cho Chat App')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
    
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    load_user_db()

    print(f"--- Tracker Server (Task 2.1 & 2.2) dang khoi dong tai {ip}:{port} ---")
    app.prepare_address(ip, port)
    app.run()