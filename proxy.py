#!/usr/bin/env python3
import socketserver
from pprint import pprint
from socket import socket

import requests

import persistence
import config


class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """
    data: bytes
    request: socket
    repository_class = persistence.RequestRepo

    def handle(self):
        # self.request is the TCP socket connected to the client
        # read in from the port using a socket
        self.data = self.request.recv(1024).strip()
        print("{} wrote:".format(self.client_address[0]))
        print(self.data)

        # pass along the request
        request_dict = self._parse_request()
        response = requests.request(**request_dict)

        # Debug output/persistence
        self.repository_class.save(request_dict, response)
        self._debug_stdout(response)

        # send back the response
        self.request.sendall(response.text.encode())

    def _debug_stdout(self, response):
        pprint(response)
        print("\n" * 2)
        print("DEBUG DATA")
        print("-" * 30)
        print("-" * 30)
        print("\n\nREQUEST:\n")
        print(self._request_str)
        print("\n\nRESPONSE:\n")
        print(response.text)

    def _parse_request(self) -> persistence.RequestDict:
        """
        Prepares a dict representation of the request data (kwargs for requests.request)
        :return:
        """
        request_lines = self.data.split(b"\r\n")
        method, url, version = request_lines[0].split(b" ")
        # Might use this later
        host = request_lines[1].strip().split(b': ')[-1]
        payload = b""
        headers = {}
        for index, line in [*enumerate(request_lines)][2:]:
            if len(line) == 0 and method in ["PUT", "POST", "PATCH"]:
                payload = b"".join(request_lines[index + 1:])
                break
            header_item = tuple(line.strip().split(b": "))
            if len(header_item) != 2:
                break
            header_name, value = header_item
            headers[header_name] = value
        request_dict = {
            'method': method, 'url': url, 'headers': headers, 'data': payload
        }
        return request_dict

    @property
    def _request_str(self) -> str:
        return self.data.decode(config.HTTP_ENCODING)


if __name__ == "__main__":
    MyTCPHandler.repository_class = persistence.RequestRepo.create(storage_type=persistence.JSON)
    # Create the server, binding to localhost on port 9999
    with socketserver.TCPServer((config.HOST, config.PORT), MyTCPHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()
