from typing import List, Iterable


def parse_lines(lines: Iterable[bytes]) -> dict:
    lines = [*lines]
    method, url, version = lines[0].split(b" ")
    # Might use this later
    host = lines[1].strip().split(b': ')[-1]
    payload = b""
    headers = {}
    for index, line in [*enumerate(lines)][2:]:
        if len(line) == 0 and method in [b"PUT", b"POST", b"PATCH"]:
            payload = b"".join(lines[index + 1:])
            break
        header_item = tuple(line.strip().split(b": "))
        if len(header_item) != 2:
            continue
        header_name, value = header_item
        headers[header_name] = value
    request_dict = {
        'method': method, 'url': url, 'headers': headers, 'data': payload
    }

    return request_dict
