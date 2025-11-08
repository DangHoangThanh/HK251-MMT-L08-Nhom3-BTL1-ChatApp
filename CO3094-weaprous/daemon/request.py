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
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
import base64
import json
from .dictionary import CaseInsensitiveDict

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = None
        #: HTTP path
        self.path = None        
        # The cookies set used to create Cookie header
        self.cookies = None
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):
        try:
            lines = request.splitlines()
            first_line = lines[0]
            method, path, version = first_line.split()

            if path == '/':
                path = '/index.html'
        except Exception:
            return None, None

        return method, path, version
             
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.lower()] = val
        return headers

    def prepare(self, request, routes=None):
        """Prepares the entire request with the given parameters."""

        # Prepare the request line from the request header
        self.method, self.path, self.version = self.extract_request_line(request)
        print("[Request] {} path {} version {}".format(self.method, self.path, self.version))

        header_section, separator, body_section = request.partition('\r\n\r\n')
        if not separator:
            header_section = request
            body_section = ''

        #
        # @bksysnet Preapring the webapp hook with WeApRous instance
        # The default behaviour with HTTP server is empty routed
        #
        # TODO manage the webapp hook in this mounting point
        #
        if routes:
            self.routes = routes
            self.hook = routes.get((self.method, self.path))
            #
            # self.hook manipulation goes here
            # ...
            #
            
            #
            #  TODO: implement the cookie function here
            #        by parsing the header            #
        self.headers = self.prepare_headers(header_section)
        self.body = body_section

        cookies_header = self.headers.get('Cookie', '')
        self.cookies = self._parse_cookie_header(cookies_header)

        if self.cookies:
            self.prepare_cookies(self._format_cookie_header(self.cookies))

        return self

    def prepare_body(self, data, files, json_data=None):
        payload = ''
        if json_data is not None:
            try:
                payload = json.dumps(json_data)
            except (TypeError, ValueError):
                payload = ''
        elif data is not None:
            if isinstance(data, (str, bytes)):
                payload = data
            elif isinstance(data, dict):
                payload = "&".join([
                    "{}={}".format(str(key), str(value)) for key, value in data.items()
                ])
            else:
                payload = str(data)
        elif files:
            payload = str(files)

        self.body = payload
        self.prepare_content_length(self.body)
        #
        # TODO prepare the request authentication
        #
        return self


    def prepare_content_length(self, body):
        #
        # TODO prepare the request authentication
        #
    # self.auth = ...
        if body is None:
            length = 0
            encoded_body = ''
        elif isinstance(body, (str, bytes)):
            encoded_body = body
            length = len(encoded_body)
        else:
            encoded_body = str(body)
            length = len(encoded_body)

        self.headers["Content-Length"] = str(length)
        self.body = encoded_body
        return self


    def prepare_auth(self, auth, url=""):
        #
        # TODO prepare the request authentication
        #
    # self.auth = ...
        if not auth:
            return self

        if isinstance(auth, (str, bytes)):
            token = auth
        elif isinstance(auth, tuple) and len(auth) == 2:
            username, password = auth
            credentials = "%s:%s" % (username, password)
            token = "Basic %s" % base64.b64encode(credentials)
        else:
            token = str(auth)

        self.auth = token
        self.headers["Authorization"] = token
        return self

    def prepare_cookies(self, cookies):
            self.headers["Cookie"] = cookies


    def _parse_cookie_header(self, cookies_header):
        cookies = CaseInsensitiveDict()
        if not cookies_header:
            return cookies

        if isinstance(cookies_header, (str, bytes)):
            cookie_pairs = cookies_header.split(';')
        else:
            cookie_pairs = cookies_header

        for pair in cookie_pairs:
            if not pair:
                continue
            if '=' not in pair:
                continue
            key, value = pair.split('=', 1)
            cookies[key.strip()] = value.strip()
        return cookies

    def _format_cookie_header(self, cookies):
        if not cookies:
            return ''
        segments = []
        for key, value in cookies.items():
            segments.append("{}={}".format(key, value))
        return '; '.join(segments)

    def build_cookie_header(self):
        return self._format_cookie_header(self.cookies)
