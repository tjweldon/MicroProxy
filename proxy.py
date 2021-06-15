#!/usr/bin/env python3
import socketserver
from pprint import pprint
from socket import socket

import requests

import history
import config
import utils


class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """
    data: bytes
    request: socket
    repository_class = history.RequestRepo

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

    def _parse_request(self) -> history.RequestDict:
        """
        Prepares a dict representation of the request data (kwargs for requests.request)
        :return:
        """
        request_lines = self.data.split(b"\r\n")
        method, url, version = request_lines[0].split(b" ")
        # Might use this later
        return utils.parse_lines(request_lines)

    @property
    def _request_str(self) -> str:
        return self.data.decode(config.HTTP_ENCODING)


if __name__ == "__main__":
    MyTCPHandler.repository_class = history.RequestRepo.create(storage_type=history.JSON)
    # Create the server, binding to localhost on port 9999
    with socketserver.TCPServer((config.HOST, config.PORT), MyTCPHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.serve_forever()
