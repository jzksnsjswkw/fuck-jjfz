from math import ceil
from random import uniform
import requests
from bs4 import BeautifulSoup
import re
import threading
import time
from alive_progress import alive_bar
from utils import print, cookie_to_dict, get_poem, query_to_dict


# 填这个
host = ''

# 和这个
cookie = ''

headers = {
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'DNT': '1',
    'Host': host,
    'Origin': 'https://' + host,
    'sec-ch-ua': '"Microsoft Edge";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Safari/605.1.15',
    'X-Requested-With': 'XMLHttpRequest',
}

cookie_dict = cookie_to_dict(cookie)
session = requests.session()
requests.utils.add_dict_to_cookiejar(session.cookies, cookie_dict)


def study_time_wrapper(rid: str, _xsrf: str):
    global cookies
    flag = False

    def stop_study_time() -> None:
        nonlocal flag
        flag = True

    url = f'https://{host}/jjfz/lesson/study_time'

    data = {
        "rid": rid,
        "study_time": "5000",
        "_xsrf": _xsrf,
    }

    def study_time() -> None:
        t = 5
        while True:
            if flag:
                return

            t += 1

            if t >= 5:
                try:
                    res = session.post(url, headers=headers, data=data)
                    if res.status_code != 200:
                        print("study_time请求失败，响应状态码出错")
                except Exception as e:
                    print("study_time请求失败", e)
                t = 0

            time.sleep(1)

    return study_time, stop_study_time


def current_time(rid: str, _xsrf: str, video_duration: float | str, title: str) -> bool:
    global cookies

    url = f'https://{host}/jjfz/lesson/current_time'
    data = {
        'rid': rid,
        "time": 0.0,
        "_xsrf": _xsrf,
    }

    number = ceil(video_duration / 30.0)

    watched_duration = 30.0
    with alive_bar(len(range(number)), calibrate=5, title=title) as bar:
        for _ in range(number):
            bar.text(get_poem())
            # 刷完
            if watched_duration == video_duration:
                return

            try:
                if video_duration - watched_duration >= 30:
                    time.sleep(30)
                    data['time'] = watched_duration + round(uniform(0, 1), 6)
                    # print(data['time'])
                    res = session.post(url, headers=headers, data=data)
                    if res.status_code != 200:
                        print('current_time 响应状态码出错')
                    watched_duration += 30

                else:
                    time.sleep(video_duration - watched_duration)

            except Exception as e:
                print('current_time err', e)

            bar()  # 显示进度


def no_current_time(video_duration: int | str, title: str) -> None:
    number = ceil(int(video_duration))
    with alive_bar(len(range(number)), calibrate=5, title=title) as bar:
        for _ in range(number):
            bar.text(get_poem())
            time.sleep(1)
            bar()  # 显示进度


def resource_record(resource_record_dict: dict, _xsrf: str) -> bool:
    url = f'https://{host}/jjfz/lesson/resource_record'
    resource_record_dict['_xsrf'] = _xsrf

    res = session.post(url, headers=headers, data=resource_record_dict).json()
    if res['code'] == 1:
        return True
    return False


def get_video_list(lesson_id: int | str, page: int | str = 1) -> list:
    url = f'https://{host}/jjfz/lesson/video?lesson_id={lesson_id}&page={page}'
    res = session.get(url, headers=headers).text

    soup = BeautifulSoup(res, 'lxml')
    li_list = soup.select('.lesson1_lists ul li')
    video_list = []

    for li in li_list:
        # 课程已完成
        if len(li.select('.lesson_pass')) == 1:
            continue

        a_list = li.select('.lesson1_a_w dl dd a')
        # 有多个视频
        if len(a_list) != 0:
            for a in a_list:
                # 视频未完成
                if len(a.get('class')) == 0:
                    video_info = {
                        'url': 'https://' + host + a.get('href'),
                        'title': a.get('title').replace('\t', ''),
                    }
                    video_list.append(video_info)

        # 只有一个视频
        else:
            video_info = {
                'url': 'https://' + host + li.find('a').get('href'),
                'title': li.find('h2').text.strip().replace('\t', ''),
            }
            video_list.append(video_info)

    # 判断分页
    a_list = soup.select('.pages a')
    for a in a_list:
        if a.string == '下一页':
            buf = query_to_dict(a.get('href').rsplit(('?'), 1)[1])
            # print(buf)
            video_list += get_video_list(buf['lesson_id'], buf['page'])

    return video_list


def get_video_info(url: str, title: str):
    def get_duration(m3u8_url: str) -> float:
        buf = session.get(m3u8_url, headers=headers).text
        a = re.findall(r'#EXTINF:(.*?),', buf)
        duration = 0.0
        for i in a:
            duration += float(i)
        return duration

    res = session.get(url, headers=headers).text

    _xsrf = re.search(r'name="_xsrf" value="(.*?)"', res).group(1)

    m3u8_url = 'https://' + host + re.findall(r"var videoSrc = '(.*?)'", res)[1]
    duration = get_duration(m3u8_url)

    buf = re.search(r'/jjfz/lesson/resource_record.*?data: \{(.*?)\}', res, re.S).group(
        1
    )
    resource_record_dict = {
        'rid': re.search(r'rid: "(.*?)"', buf).group(1),
        'resource_id': re.search(r'resource_id: "(.*?)"', buf).group(1),
        'video_id': re.search(r'video_id: "(.*?)"', buf).group(1),
        'lesson_id': re.search(r'lesson_id: "(.*?)"', buf).group(1),
    }

    study_time_rid = re.search(
        r'/jjfz/lesson/study_time.*?rid: "(\d*)"', res, re.S
    ).group(1)

    try:
        current_time_rid = re.search(
            r'/jjfz/lesson/current_time.*?rid: "(\d*)"', res, re.S
        ).group(1)
    except Exception:
        current_time_rid = None

    video_info = {
        'title': title,
        '_xsrf': _xsrf,
        'duration': duration,
        'resource_record_dict': resource_record_dict,
        'study_time_rid': study_time_rid,
        'current_time_rid': current_time_rid,
    }
    return video_info


def get_course_list() -> list:
    url = f'https://{host}/jjfz/lesson'
    res = session.get(url, headers=headers).text

    soup = BeautifulSoup(res, 'lxml')
    buf = soup.select('.lesson_c_ul li')

    course_list = []
    for i in buf:
        if len(i.select('.lesson_center_a a')) == 1:
            a = i.find('a')
            course_info = {
                'lesson_id': a.get('href').rsplit('lesson_id=', 1)[1],
                'course_name': a.text.strip(),
            }
            # print(course_info)
            course_list.append(course_info)

    return course_list


def fuck(video_info: dict) -> None:
    study_time, stop_study_time = study_time_wrapper(
        video_info['study_time_rid'], video_info['_xsrf']
    )

    study_time_thread = threading.Thread(target=study_time)

    if not video_info['current_time_rid'] is None:
        current_time_thread = threading.Thread(
            target=current_time,
            args=(
                video_info['current_time_rid'],
                video_info['_xsrf'],
                video_info['duration'],
                video_info['title'],
            ),
        )
    else:
        current_time_thread = threading.Thread(
            target=no_current_time, args=(video_info['duration'], video_info['title'])
        )

    study_time_thread.start()
    current_time_thread.start()

    current_time_thread.join()
    resource_record(video_info['resource_record_dict'], video_info['_xsrf'])
    stop_study_time()
    study_time_thread.join()


course_list = get_course_list()
headers['Referer'] = f"https://{host}/jjfz/lesson"
for course in course_list:
    # print('course:', course)
    print(course['course_name'])
    video_list = get_video_list(course['lesson_id'])

    for video in video_list:
        # print('video', video)
        video_info = get_video_info(**video)
        # print('video_info', video_info)
        headers['Referer'] = video['url']
        fuck(video_info)
