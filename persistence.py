from __future__ import annotations
import datetime
import json
import time
from typing import Dict, Union, Type, Optional as Opt

import requests
import urllib3

import config

Headers = Dict[bytes, bytes]
RequestDict = Dict[str, Union[bytes, Headers]]  # Consider implementing with namedtuple

JSON = 0


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
    def save(cls, request_dict: dict, response: requests.Response, host: Opt[str] = None) -> None:
        """
        Creates a persistent machine-readable record of the HTTP request/response pair
        :param request_dict:
        :param response:
        :param host:
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
    def save(cls, request_dict: RequestDict, response: requests.Response, host: Opt[str] = None) -> None:
        url = request_dict["url"].decode(config.HTTP_ENCODING)
        if host is None:
            host = urllib3.util.parse_url(url).host
        iso_dt = datetime.datetime.now().isoformat()
        method = request_dict["method"].decode(config.HTTP_ENCODING)
        body = request_dict.get("data", None)

        # Example: 10000000.000_2000-01-01T00:00:00_GET_google.com.json
        filename = (
            "{:.3f}".format(time.time()) +
            f"_{iso_dt}_{method}_{host}.json"
        )

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

        print(record)

        # write to filesystem
        with open(cls.storage_path + filename, "w") as file:
            file.write(json.dumps(record))
