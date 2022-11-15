import re
import json
import time
from datetime import datetime
from threading import Lock

print_ = print
lock = Lock()


def print(text="", *args, **kwargs) -> None:
    """清除输出缓冲区

    加锁防止输出错乱

    Args:
        text (str, optional): _description_. Defaults to "".
    """
    with lock:
        print_(text, *args, **kwargs, flush=True)


def get_timestamp() -> int:
    """获取JS时间戳

    Returns:
        int: JS时间戳
    """
    return int(time.time() * 1000)


def print_now() -> None:
    """打印当前时间"""
    print(datetime.now())


def cookie_to_dict(cookie: str) -> dict:
    cookie_dict = {}
    for i in cookie.split('; '):
        key, value = i.split('=', 1)
        cookie_dict[key] = value
    return cookie_dict


def query_to_dict(query_str: str) -> dict:
    """查询字符串转字典

    Args:
        query_str (str)

    Returns:
        dict
    """
    if query_str.startswith('?'):
        query_str = query_str[1:]

    query_dict = {}
    for i in query_str.split("&"):
        key, value = i.split("=")
        query_dict[key] = value

    return query_dict


def is_json(s: str) -> bool:
    """判断字符串是否是JSON格式

    Args:
        s (str)

    Returns:
        bool
    """
    try:
        json.loads(s)
    except ValueError:
        return False
    return True


def curl_to_python(curl_str: str) -> tuple[str, list, str]:
    """curl转python

    Args:
        curl_str (str)

    Returns:
        tuple[str, list, str]: (python_code, python_dict, req_method)
    """
    python_code = ""
    python_dict = {}

    curl = curl_str.split(' -H ')
    req_method = curl[0].rsplit(' ', 1)[1]
    if req_method == 'GET':
        curl[-1], url = re.findall(r'(".*?") "(.*?)"', curl[-1])[0]

        headers = {}
        for i in curl[1:]:
            k, v = re.findall(r'"(.*?): (.*?)"', i)[0]
            headers[k.lower()] = v

        python_code += f"url = '{url}'\n"
        python_code += f"headers = {headers}\n"
        python_code += "res = requests.get(url, headers=headers)\n"
        # print(f"url = '{url}'")
        # print(f"headers = {headers}")
        # print("res = requests.get(url, headers=headers)")

        python_dict['url'] = url
        python_dict['headers'] = headers

    elif req_method == 'POST':
        curl[-1], temp = curl[-1].split(' -d ')
        data, url = re.findall(r'"(.*?)" "(.*?)"', temp)[0]
        headers = {}
        for i in curl[1:]:
            k, v = re.findall(r'"(.*?): (.*?)"', i)[0]
            headers[k.lower()] = v

        python_code += f"url = '{url}'\n"
        python_code += f"headers = {headers}\n"
        # print(f"url = '{url}'")
        # print(f"headers = {headers}")

        python_dict['url'] = url
        python_dict['headers'] = headers
        if is_json(data):
            python_code += f"data = {json.dumps(data)}\n"
            python_code += "res = requests.post(url, headers=headers, json=data)\n"
            # print(f"data = {json.dumps(data)}")
            # print("res = requests.post(url, headers=headers, json=data)")

            python_dict['data'] = json.dumps(data)
        else:
            python_code += f"data = {query_to_dict(data)}\n"
            python_code += "res = requests.post(url, headers=headers, data=data)\n"
            # print(f"data = {query_to_dict(data)}")
            # print("res = requests.post(url, headers=headers, data=data)")

            python_dict['data'] = query_to_dict(data)

    python_code += "print(res.text)\n"
    # print("print(res.text)")
    # print(python_code)
    return python_code, python_dict, req_method
