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
from daemon.utils import get_auth_from_url

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
             
    def prepare_headers(self, header_data):
        """
        Prepares the given HTTP headers.
        
        :param header_data: (str) Raw HTTP header data.
        :rtype: dict
        """
        
        lines = header_data.split('\r\n')
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
        
        if not routes == {}:
            self.routes = routes
            self.hook = routes.get((self.method, self.path))
            #
            # self.hook manipulation goes here
            # ...
            #

        self.headers = self.prepare_headers(header_section)
            
        self.body = body_section

        cookies = self.headers.get('cookie', '')
            #
            #  TODO: implement the cookie function here
            #        by parsing the header            #
        self.cookies = self._parse_cookie_header(cookies)

        # Thừa
        # if self.cookies:
        #     self.prepare_cookies(self._format_cookie_header(self.cookies))

        return


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

    # def _format_cookie_header(self, cookies):
    #     if not cookies:
    #         return ''
    #     segments = []
    #     for key, value in cookies.items():
    #         segments.append("{}={}".format(key, value))
    #     return '; '.join(segments)

    # def build_cookie_header(self):
    #     return self._format_cookie_header(self.cookies)
