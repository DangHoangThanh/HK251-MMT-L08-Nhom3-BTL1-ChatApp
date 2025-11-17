# chat_ui.py (Phiên bản GUI Đa kênh)
import socket
import threading
import requests # Bắt buộc: pip install requests
import json
import time
import sys
import os  
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox, Listbox, Frame, PanedWindow, Label
from queue import Queue

# -----------------------------------------------------
# CÀI ĐẶT
# -----------------------------------------------------
TRACKER_URL = "http://127.0.0.1:8080"
HEARTBEAT_INTERVAL = 15
AUTO_REFRESH_INTERVAL = 5000 

class ChatClientGUI:
    def __init__(self):
        self.tracker_url = TRACKER_URL
        self.username = None
        self.p2p_port = 0
        self.p2p_server_socket = None
        self.local_ip = "127.0.0.1"

        self.current_chat_context = None 
        self.session = requests.Session()
        self.message_queue = Queue() 
        
        self.chat_history = {}
        self.unread_messages = {}
        self.channels = ["chung"] 
        self.peers = {}

        # Xây dựng GUI
        self.root = tk.Tk()
        self.root.title("P2P Chat Client")
        self.build_gui()

    # =============================================================
    # QUẢN LÝ FILE LỊCH SỬ
    # =============================================================
    def _get_history_filename(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(current_dir, 'data')
        if not os.path.exists(data_dir):
            try: os.makedirs(data_dir)
            except: return f"history_{self.username}.json"
        return os.path.join(data_dir, f"history_{self.username}.json")

    def _load_local_history(self):
        filename = self._get_history_filename()
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    self.chat_history = json.load(f)
                print(f"[INFO] Đã tải lịch sử từ {filename}")
            except Exception as e: print(f"[ERR] Lỗi đọc file: {e}")

    def _save_local_history(self):
        if not self.username: return
        filename = self._get_history_filename()
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.chat_history, f, ensure_ascii=False, indent=4)
        except Exception as e: print(f"[ERR] Không lưu được lịch sử: {e}")

    # =============================================================
    # XÂY DỰNG GIAO DIỆN (GUI)
    # =============================================================
    def build_gui(self):
        self.root.geometry("800x600")
        paned = PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True)

        left_frame = Frame(paned, width=220, bg="#f0f0f0")
        left_frame.pack_propagate(False)
        tk.Label(left_frame, text="Danh Sách Chat", font=("Segoe UI", 12, "bold"), bg="#f0f0f0").pack(pady=10)
        tk.Button(left_frame, text="⟳ Làm mới", command=self._refresh_contacts).pack(fill=tk.X, padx=10)
        self.contact_listbox = Listbox(left_frame, font=("Segoe UI", 11), bd=0)
        self.contact_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.contact_listbox.bind("<<ListboxSelect>>", self._on_contact_select)
        paned.add(left_frame, width=220)

        right_frame = Frame(paned, bg="white")
        self.header_label = Label(right_frame, text="Chọn hội thoại...", font=("Segoe UI", 13, "bold"), bg="white", fg="#333", pady=10, anchor="w")
        self.header_label.pack(fill=tk.X, padx=15)
        Frame(right_frame, height=1, bg="#ddd").pack(fill=tk.X)
        self.chat_area = scrolledtext.Text(right_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 11), bd=0, padx=10, pady=10)
        self.chat_area.pack(fill=tk.BOTH, expand=True)
        
        btm_frame = Frame(right_frame, bg="#f0f0f0", height=60)
        btm_frame.pack(fill=tk.X, side=tk.BOTTOM)
        btm_frame.pack_propagate(False)
        self.entry_box = tk.Entry(btm_frame, font=("Segoe UI", 11), bd=1, relief=tk.SOLID)
        self.entry_box.bind("<Return>", self._on_send_click)
        self.entry_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        tk.Button(btm_frame, text="Gửi ➤", command=self._on_send_click, bg="#0078D7", fg="white", font=("Segoe UI", 10, "bold")).pack(side=tk.RIGHT, padx=10)
        
        paned.add(right_frame)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    # =============================================================
    # GUI LOGIC
    # =============================================================
    def _on_send_click(self, event=None):
        text = self.entry_box.get()
        if not text or not self.current_chat_context: return
        self.entry_box.delete(0, tk.END)
        
        ctx = self.current_chat_context
        payload = {"from": self.username, "message": text}
        
        if ctx not in self.chat_history: self.chat_history[ctx] = []
        self.chat_history[ctx].append(payload)
        self._save_local_history()
        self._load_chat_history(ctx)
        
        if ctx.startswith("dm_"):
            target = ctx.split("dm_")[1]
            payload["type"] = "direct_message"
            payload["channel"] = None
            threading.Thread(target=self._send_direct_message, args=(target, payload), daemon=True).start()
        else:
            payload["type"] = "channel_message"
            payload["channel"] = ctx
            threading.Thread(target=self._broadcast_to_channel, args=(ctx, payload), daemon=True).start()

    def _on_contact_select(self, event=None):
        try:
            if not self.contact_listbox.curselection(): return
            item = self.contact_listbox.get(self.contact_listbox.curselection()[0])
            if item.startswith("(group) "):
                raw = item.replace("(group) ", "").split(" (")[0]
                self.current_chat_context = raw
                self.header_label.config(text=f"Kênh Nhóm: {raw}")
            else:
                raw = item.split(" (")[0]
                self.current_chat_context = f"dm_{raw}"
                self.header_label.config(text=f"Chat riêng với: {raw}")
            self.unread_messages.pop(self.current_chat_context, None)
            self._update_contact_list_display()
            self._load_chat_history(self.current_chat_context)
        except: pass

    def _load_chat_history(self, ctx):
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.delete(1.0, tk.END)
        for msg in self.chat_history.get(ctx, []):
            sender = "Me" if msg['from'] == self.username else msg['from']
            tag = 'me' if sender == "Me" else 'sys' if sender == "System" else 'peer'
            prefix = "[Offline] " if msg.get("is_offline") else ""
            self.chat_area.insert(tk.END, f"[{sender}]: {prefix}{msg['message']}\n", tag)
        
        self.chat_area.tag_config('me', foreground="#0078D7", font=("Segoe UI", 11, "bold"))
        self.chat_area.tag_config('sys', foreground="red", font=("Segoe UI", 11, "italic"))
        self.chat_area.tag_config('peer', foreground="#333", font=("Segoe UI", 11))
        self.chat_area.configure(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def _on_closing(self):
        if messagebox.askokcancel("Thoát", "Bạn muốn thoát?"):
            try: self.session.post(f"{self.tracker_url}/logout", json={"username": self.username})
            except: pass
            self.root.destroy()
            sys.exit()

    # =============================================================
    # BACKGROUND TASKS
    # =============================================================
    def _check_incoming_messages(self):
        while not self.message_queue.empty():
            ctx, msg = self.message_queue.get()
            if ctx == "[SYSTEM]": 
                print(f"[LOG] {msg['message']}")
            else:
                if ctx not in self.chat_history: self.chat_history[ctx] = []
                self.chat_history[ctx].append(msg)
                self._save_local_history()
                if ctx == self.current_chat_context: self._load_chat_history(ctx)
                else:
                    self.unread_messages[ctx] = self.unread_messages.get(ctx, 0) + 1
                    self._update_contact_list_display()
        self.root.after(200, self._check_incoming_messages)

    def _auto_refresh_loop(self):
        if self.username:
            self._refresh_contacts()
            threading.Thread(target=self._fetch_offline_messages, daemon=True).start()
        self.root.after(AUTO_REFRESH_INTERVAL, self._auto_refresh_loop)

    # =============================================================
    # NETWORK & LOGIC (STORE AND FORWARD - ĐÃ FIX)
    # =============================================================
    def _send_offline_to_server(self, target_user, payload):
        """Gửi tin nhắn offline và kiểm tra phản hồi của Server"""
        try:
            print(f"[INFO] Gửi Offline cho {target_user}...")
            resp = self.session.post(f"{self.tracker_url}/api/send_offline", json={
                "target_user": target_user, "payload": payload
            })
            
            # [FIX] Kiểm tra xem Server có thực sự nhận không
            if resp.status_code == 200:
                self.message_queue.put((
                    f"dm_{target_user}" if payload['type']=='direct_message' else payload['channel'], 
                    {"from": "System", "message": f"Người dùng {target_user} offline. Đã lưu tin nhắn lên Server."}
                ))
            else:
                # Nếu Server trả về lỗi (404, 500...), báo cho người dùng biết
                print(f"[ERR] Server rejected offline msg: {resp.status_code} {resp.text}")
                self.message_queue.put((
                    f"dm_{target_user}" if payload['type']=='direct_message' else payload['channel'], 
                    {"from": "System", "message": f"LỖI: Server không lưu được tin nhắn (Code {resp.status_code}). Hãy kiểm tra lại Server!"}
                ))

        except Exception as e: 
            print(f"[ERR] Send Offline Fail: {e}")
            self.message_queue.put((
                f"dm_{target_user}" if payload['type']=='direct_message' else payload['channel'], 
                {"from": "System", "message": f"LỖI MẠNG: Không gửi được lên Server: {e}"}
            ))

    def _fetch_offline_messages(self):
        try:
            resp = self.session.get(f"{self.tracker_url}/api/fetch_offline")
            if resp.status_code == 200:
                msgs = resp.json().get("messages", [])
                if msgs:
                    print(f"[INFO] Nhận được {len(msgs)} tin nhắn offline.")
                    for msg in msgs:
                        ctx = f"dm_{msg.get('from')}" if msg.get("type") == "direct_message" else msg.get("channel")
                        if ctx: self.message_queue.put((ctx, msg))
        except: pass

    def _p2p_listener_thread(self):
        try:
            self.p2p_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.p2p_server_socket.bind(('0.0.0.0', 0))
            self.p2p_port = self.p2p_server_socket.getsockname()[1]
            self.p2p_server_socket.listen(10)
            self.message_queue.put(("[SYSTEM]", {"message": f"Listening on {self.local_ip}:{self.p2p_port}"}))
            while True:
                conn, addr = self.p2p_server_socket.accept()
                threading.Thread(target=self._handle_peer_connection, args=(conn,), daemon=True).start()
        except Exception as e: print(f"P2P Error: {e}")

    def _handle_peer_connection(self, conn):
        with conn:
            try:
                data = conn.recv(4096)
                if not data: return
                msg = json.loads(data.decode('utf-8'))
                ctx = f"dm_{msg.get('from')}" if msg.get("type") == "direct_message" else msg.get("channel")
                if ctx: self.message_queue.put((ctx, msg))
            except: pass

    def _send_p2p(self, ip, port, payload):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                s.connect((ip, int(port)))
                s.sendall(json.dumps(payload).encode('utf-8'))
            return True
        except: return False

    def _send_direct_message(self, target, payload):
        self._refresh_peers_data()
        if target in self.peers:
            info = self.peers[target]
            if not self._send_p2p(info['ip'], info['port'], payload):
                self._send_offline_to_server(target, payload)
        else: self._send_offline_to_server(target, payload)

    def _broadcast_to_channel(self, channel, payload):
        try:
            resp = self.session.post(f"{self.tracker_url}/channels/peers", json={"channel_name": channel})
            if resp.status_code == 200:
                peers = resp.json()
                for user, info in peers.items():
                    if user != self.username:
                        if not self._send_p2p(info['ip'], info['port'], payload):
                            self._send_offline_to_server(user, payload)
        except: pass

    def _refresh_peers_data(self):
        try:
            resp = self.session.get(f"{self.tracker_url}/get-peers")
            if resp.status_code == 200: self.peers = resp.json()
        except: pass

    def _refresh_contacts(self):
        self._refresh_peers_data()
        try:
            resp = self.session.get(f"{self.tracker_url}/channels/list")
            self.channels = resp.json().get("channels", ["chung"]) if resp.status_code == 200 else ["chung"]
        except: self.channels = ["chung"]
        self._update_contact_list_display()

    def _update_contact_list_display(self):
        self.contact_listbox.delete(0, tk.END)
        for ch in self.channels:
            name = f"(group) {ch} ({self.unread_messages.get(ch, 0)})" if self.unread_messages.get(ch, 0) > 0 else f"(group) {ch}"
            self.contact_listbox.insert(tk.END, name)
            if ch == self.current_chat_context: self.contact_listbox.itemconfig(tk.END, {'bg': '#0078D7', 'fg': 'white'})
        for user in self.peers:
            if user == self.username: continue
            key = f"dm_{user}"
            name = f"{user} ({self.unread_messages.get(key, 0)})" if self.unread_messages.get(key, 0) > 0 else user
            self.contact_listbox.insert(tk.END, name)
            if key == self.current_chat_context: self.contact_listbox.itemconfig(tk.END, {'bg': '#0078D7', 'fg': 'white'})

    def _heartbeat_thread(self):
        while True:
            try: 
                self.session.get(f"{self.tracker_url}/heartbeat")
                time.sleep(HEARTBEAT_INTERVAL)
            except: time.sleep(HEARTBEAT_INTERVAL)

    # =============================================================
    # MAIN RUN
    # =============================================================
    def run(self):
        self.root.withdraw()
        threading.Thread(target=self._p2p_listener_thread, daemon=True).start()
        time.sleep(1)

        while not self.username:
            u = simpledialog.askstring("Login", "Username:", parent=self.root)
            if not u: sys.exit()
            p = simpledialog.askstring("Login", "Password:", show='*', parent=self.root)
            if not p: sys.exit()
            
            data = {"username": u, "password": p, "IP": self.local_ip, "Port": self.p2p_port}
            print(f"\n[DEBUG] Login: {data}")

            try:
                resp = self.session.post(f"{self.tracker_url}/api/login", json=data)
                if not resp.text.strip():
                    messagebox.showerror("Lỗi", "Server trả về rỗng")
                    continue
                try: res_json = resp.json()
                except: 
                    messagebox.showerror("Lỗi JSON", resp.text)
                    continue
                
                if res_json.get("login") == "success":
                    self.username = u
                    self._load_local_history() 

                    self.root.deiconify()
                    self.root.title(f"Chat: {self.username} (Port: {self.p2p_port})")
                    
                    self.session.post(f"{self.tracker_url}/register", json={"port": self.p2p_port})
                    self.session.post(f"{self.tracker_url}/channels/join", json={"channel_name": "chung"})
                    
                    self._refresh_contacts()
                    self._check_incoming_messages() 
                    self._auto_refresh_loop()
                    threading.Thread(target=self._heartbeat_thread, daemon=True).start()
                else:
                    try:
                        reg_resp = self.session.post(f"{self.tracker_url}/register", json=data)
                        if reg_resp.json().get("status") == "registered":
                            messagebox.showinfo("Info", "Đã đăng ký. Hãy Login lại.")
                        else: messagebox.showerror("Lỗi", res_json.get("reason", "Failed"))
                    except: messagebox.showerror("Lỗi", "Register failed.")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Kết nối thất bại: {e}")
                sys.exit()

        self.root.mainloop()

if __name__ == "__main__":
    ChatClientGUI().run()