#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict


class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()


    def handle_client(self, conn, addr, routes):
        """
        Simplified workflow:
        1. Read the request.
        2. If the target is an App with a hook, run the hook.
        3. Otherwise, return the corresponding static file.
        """

        # Connection handler.
        self.conn = conn        
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = self.response

        try:
            ############################
            # Phiên bản lấy HTTP chuẩn
            ############################

            # 1. ĐỌC REQUEST (Giữ lại code đọc recv TỐT NHẤT của bạn)
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = conn.recv(1024)
                if not chunk: 
                    break
                data += chunk
            
            header_data, _, body_data = data.partition(b"\r\n\r\n")
            msg_header_only = header_data.decode('utf-8', 'ignore')
            
            # 2. Phân tích header (chỉ header)
            # Dùng 1 đối tượng Request TẠM THỜI để đọc Content-Length
            temp_req = Request()
            temp_req.prepare(msg_header_only, routes) 
            
            content_length = int(temp_req.headers.get('content-length', 0))
            
            # 3. Đọc phần body còn lại (nếu cần)
            while len(body_data) < content_length:
                bytes_to_read = content_length - len(body_data)
                chunk = conn.recv(bytes_to_read)
                if not chunk:
                    break
                body_data += chunk
                
            # 4. Chuẩn bị lại request CHÍNH THỨC với body đầy đủ
            msg = header_data.decode('utf-8', 'ignore') + "\r\n\r\n" + body_data.decode('utf-8', 'ignore')
            req.prepare(msg, routes) # req.hook được gán ở đây

            if not req.method:
                 print("[HttpAdapter] Request loi, dong ket noi.")
                 conn.close()
                 return


            # msg = conn.recv(4096).decode()
            # if not msg:
            #     print("[HttpAdapter] Client disconnected.")
            #     conn.close()
            #     return

            # req.prepare(msg, routes)
            # if not req.method:
            #     print("[HttpAdapter] Malformed request, closing connection.")
            #     conn.close()
            #     return

            # 1. ƯU TIÊN HÀNG ĐẦU: WeApRous (Task 2.1 & 2.2)
            # Nếu req.prepare tìm thấy 1 route (ví dụ /login, /register)
            # nó sẽ gán hàm (ví dụ: hàm login) vào req.hook
            if req.hook:
                print(f"[HttpAdapter] Hooking to route: {req.method} {req.path}")
                try:
                    hook_response = req.hook(headers=req.headers, body=req.body) 
                    
                    # Kịch bản 1: Lỗi 401 (API trả về lỗi, ví dụ: /index.html)
                    # (Kiểm tra xem hook_response có phải là tuple (401, ...))
                    if isinstance(hook_response, tuple) and hook_response[0] == 401:
                        print("[HttpAdapter] Hook tra ve 401. Dang phuc vu trang 401.html")
                        resp.status_code = 401
                        req.path = '/401.html' # Đổi path sang trang lỗi
                        req.hook_response = None # Xóa hook để ép chạy logic file tĩnh

                    # Kịch bản 2: Lỗi 404 (API trả về lỗi, ví dụ: /get-peers)
                    elif isinstance(hook_response, tuple) and hook_response[0] == 404:
                        print("[HttpAdapter] Hook tra ve 404. Dang phuc vu trang 404.html")
                        resp.status_code = 404
                        req.path = '/404.html' # Đổi path sang trang lỗi
                        req.hook_response = None # Xóa hook để ép chạy logic file tĩnh

                    # Kịch bản 3: Tín hiệu Magic (Login/Index thành công)
                    elif (isinstance(hook_response, dict) and 
                          hook_response.get("__pass_through__") == True):
                        # (Logic "Tín hiệu Magic" cho /index.html)
                        req.username = hook_response.get("username")
                        req.hook_response = None 
                        
                    elif (isinstance(hook_response, tuple) and len(hook_response) >= 2 and 
                          isinstance(hook_response[1], dict) and 
                          hook_response[1].get("__pass_through__") == True):
                        # (Logic "Tín hiệu Magic" cho /login)
                        req.username = hook_response[1].get("username")
                        req.hook_response = None 
                        if req.path == '/login':
                            req.path = '/index.html' 
                        if len(hook_response) == 3:
                            resp.headers.update(hook_response[2]) # Giữ Set-Cookie
                    
                    # Kịch bản 4: API bình thường (trả về JSON)
                    else:
                        req.hook_response = hook_response 
                    # --- KẾT THÚC SỬA LỖI 401/404 ---

                except Exception as exc:
                    req.hook_response = None
                    print(f"[HttpAdapter] Error khi chay hook: {exc}")
            
            # 2. FALLBACK: Phục vụ file tĩnh
            # (Nếu không có hook, ví dụ: GET /login.html, GET /style.css)
            else:
                print(f"[HttpAdapter] No hook. Phuc vu file tinh: {req.path}")
                # Không cần làm gì. 
                # response.py sẽ tự động tìm file và gán status 200
            
            # 3. BUILD RESPONSE
            response_bytes = resp.build_response(req)
            conn.sendall(response_bytes)

        except Exception as e:
            print(f"[HttpAdapter] Loi khong ngo toi: {e}")
        finally:
            conn.close()

    # @property
    # def extract_cookies(self, req, resp):
    #     """
    #     Build cookies from the :class:`Request <Request>` headers.

    #     :param req:(Request) The :class:`Request <Request>` object.
    #     :param resp: (Response) The res:class:`Response <Response>` object.
    #     :rtype: cookies - A dictionary of cookie key-value pairs.
    #     """
    #     cookies = {}
    #     for header in headers:
    #         if header.startswith("Cookie:"):
    #             cookie_str = header.split(":", 1)[1].strip()
    #             for pair in cookie_str.split(";"):
    #                 key, value = pair.strip().split("=")
    #                 cookies[key] = value
    #     return cookies

    # def build_response(self, req, resp):
    #     """Builds a :class:`Response <Response>` object 

    #     :param req: The :class:`Request <Request>` used to generate the response.
    #     :param resp: The  response object.
    #     :rtype: Response
    #     """
    #     response = Response()

    #     # Set encoding.
    #     response.encoding = get_encoding_from_headers(response.headers)
    #     response.raw = resp
    #     response.reason = response.raw.reason

    #     if isinstance(req.url, bytes):
    #         response.url = req.url.decode("utf-8")
    #     else:
    #         response.url = req.url

    #     # Add new cookies from the server.
    #     response.cookies = extract_cookies(req)

    #     # Give the Response some context.
    #     response.request = req
    #     response.connection = self

    #     return response

    # def get_connection(self, url, proxies=None):
        # """Returns a url connection for the given URL. 

        # :param url: The URL to connect to.
        # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        # :rtype: int
        # """

        # proxy = select_proxy(url, proxies)

        # if proxy:
            # proxy = prepend_scheme_if_needed(proxy, "http")
            # proxy_url = parse_url(proxy)
            # if not proxy_url.host:
                # raise InvalidProxyURL(
                    # "Please check proxy URL. It is malformed "
                    # "and could be missing the host."
                # )
            # proxy_manager = self.proxy_manager_for(proxy)
            # conn = proxy_manager.connection_from_url(url)
        # else:
            # # Only scheme should be lower case
            # parsed = urlparse(url)
            # url = parsed.geturl()
            # conn = self.poolmanager.connection_from_url(url)

        # return conn


    # def add_headers(self, request):
    #     """
    #     Add headers to the request.

    #     This method is intended to be overridden by subclasses to inject
    #     custom headers. It does nothing by default.

        
    #     :param request: :class:`Request <Request>` to add headers to.
    #     """
    #     pass

    # def build_proxy_headers(self, proxy):
    #     """Returns a dictionary of the headers to add to any request sent
    #     through a proxy. 

    #     :class:`HttpAdapter <HttpAdapter>`.

    #     :param proxy: The url of the proxy being used for this request.
    #     :rtype: dict
    #     """
    #     headers = {}
    #     #
    #     # TODO: build your authentication here
    #     #       username, password =...
    #     # we provide dummy auth here
    #     #
        
    #     # NOT USED
    #     auth = get_auth_from_url(proxy)

    #     if auth:
    #         headers["Proxy-Authorization"] = auth

    #     return headers