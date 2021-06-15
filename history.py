from __future__ import annotations

import dataclasses
import datetime
import glob
import json
import ntpath
import os
import time
from typing import Dict, Union, Type, Optional as Opt, Any, Tuple

import requests
import urllib3

import config

Headers = Dict[bytes, bytes]
RequestDict = Dict[str, Union[bytes, Headers]]  # Consider implementing with namedtuple

JSON = 0


class Parts:
    NONE: slice = slice(0)
    HEAD: slice = slice(2)
    BODY: slice = slice(2, None)
    ALL: slice = slice(None)


crlf = "\r\n"


@dataclasses.dataclass
class RequestRecord:
    method: str
    url: str
    headers: Dict[str, str]
    body: str

    def __init__(self, **kwargs):
        for attr_name, attr_val in kwargs.items():
            setattr(self, attr_name, attr_val)
        self._identifier = None

    @property
    def host(self) -> str:
        return urllib3.util.parse_url(self.url).host

    @property
    def identifier(self) -> str:
        return self._identifier

    def raw(self, parts: slice = Parts.ALL) -> str:
        """
        part (str) can have the string literal values:
         -
        :param parts:
        :return:
        """
        try:
            return "\r\n".join(open(config.RAW_REQ_PATH + self._identifier + ".http").readlines())
        except FileNotFoundError:
            first_line = f"{self.method} {self.url} HTTP/1.1"
            host_line = f"Host: {self.host}"
            headers = [f"{h_name}: {h_val}" for h_name, h_val in self.headers.items()]
            empty_line = ""
            request_head = "\r\n".join([
                first_line,
                host_line,
                *headers,
            ])
            raw = crlf.join([
                request_head,
                empty_line,
                self.body
                ][parts])

        return raw

    @identifier.setter
    def identifier(self, identifier) -> None:
        self._identifier = identifier


@dataclasses.dataclass
class ResponseRecord:
    status: int
    headers: Dict[str, str]
    body: bytes


@dataclasses.dataclass
class HTTPRecord:
    request: RequestRecord
    response: ResponseRecord


class RequestRepo:
    @staticmethod
    def create(storage_type=JSON) -> Type[JsonRequestRepo]:
        """
        Factory method for concrete implementations
        :param storage_type:
        :return:
        """
        return [
            JsonRequestRepo,  # Plan to include an sqlite implementation too
        ][storage_type]

    @classmethod
    def save(
            cls, request_dict: dict, response: requests.Response, host: Opt[str] = None, raw: Opt[bytes] = None
    ) -> None:
        """
        Creates a persistent machine-readable record of the HTTP request/response pair
        :param raw:
        :param request_dict:
        :param response:
        :param host:
        :return:
        """
        raise NotImplementedError

    @classmethod
    def get_latest(cls) -> HTTPRecord:
        """
        Returns an HTTPRecord instance of the latest request to have been persisted
        :return:
        """
        raise NotImplementedError


class JsonRequestRepo(RequestRepo):
    """
    Stores requests in systematically named json files
    Example: ./data/json/10000000.000_2000-01-01T00:00:00_GET_google.com.search.json
    """
    storage_path = "./data/json/"

    @classmethod
    def save(
            cls, request_dict: RequestDict, response: requests.Response, host: Opt[str] = None, raw: Opt[bytes] = None
    ) -> None:
        url = request_dict["url"].decode(config.HTTP_ENCODING)
        if host is None:
            host = urllib3.util.parse_url(url).host
        iso_dt = datetime.datetime.now().isoformat()
        method = request_dict["method"].decode(config.HTTP_ENCODING)
        body = request_dict.get("data", None)

        # Example: 10000000.000_2000-01-01T00:00:00_GET_google.com.json
        identifier = (
            "{:.3f}".format(time.time()) +
            f"_{iso_dt}_{method}_{host}"
        )

        filename = identifier + ".json"

        if raw:
            with open(config.RAW_REQ_PATH + identifier + ".http", "w+") as raw_file:
                raw_file.write(raw.decode())

        # request/response serialisation
        codec = config.HTTP_ENCODING
        record = {
            "request": {
                "method": method,
                "url": url,
                "headers": {
                    k.decode(codec): v.decode(codec) for k, v in request_dict["headers"].items()
                },
                "body": body.decode()  # encoding could be pulled from headers
            },
            "response": {
                "status": response.status_code,
                "headers": {**response.headers},
                "body": response.content.decode()  # This needs a bit more attention
            }
        }

        # write to filesystem
        with open(cls.storage_path + filename, "w") as file:
            file.write(json.dumps(record))

    @classmethod
    def get_latest(cls) -> HTTPRecord:
        json_records = sorted(filter(os.path.isfile, glob.glob(cls.storage_path + '*')))
        latest_record = json_records[-1]
        dict_record = json.load(open(latest_record, "r"))
        req = RequestRecord(**dict_record.get("request", {}))
        req.identifier = ntpath.basename(".".join(latest_record.split(".")[:-1]))
        resp = ResponseRecord(**dict_record.get("response", {}))

        return HTTPRecord(request=req, response=resp)

