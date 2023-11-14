import re
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytube

from APICaller import APICaller


def __get_frame(video_capture: cv2.VideoCapture) -> np.ndarray:
    """
    生成视频截图
    :param video_capture: 视频流链接
    :return: 截图
    """
    total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = video_capture.get(cv2.CAP_PROP_FPS)
    start_frame = total_frames * 2 // 3  # 从视频2/3处开始

    for i in range(int(total_frames - fps), start_frame, int(-2 * fps)):
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = video_capture.read()
        if ret:
            print(f"截图在 {i // fps}s", end="\t")
            h, w = frame.shape[:2]
            yield frame[h // 6:h, w // 4:w * 3 // 4]  # 保留字幕部分


def __find_pwd(text: str) -> str:
    # 判断文本中是否包含"密码"
    if "密码" in text:
        num_list = re.findall(r'\d+', text)
        word = "".join(num_list)
        print(f"\n候选 {word}")
        return "".join(num_list)


def _get_pwd_by_ocr(apicaller: APICaller, image: np.ndarray) -> str:
    """
    调用ocr获得密码
    :param apicaller: APICaller
    :param image: 截图
    :return: 候选密码文本
    """
    apicaller.img_to_base64(image)  # 传入截图
    result = apicaller.digital_ocr()  # 调用ocr
    words_result = result.get("words_result")
    num = result.get("words_result_num")

    # 遍历截图中的候选词
    for i in range(int(num)):
        text = words_result[i]["words"]

        yield __find_pwd(text)


def _get_pwd_from_caption(subtitles: list[pytube.Caption]) -> str:
    """
    遍历字幕获得密码
    :param subtitles:字幕
    :return: 候选密码文本
    """
    for caption in subtitles:
        # 遍历字幕
        xml_str = caption.xml_captions

        root = ET.fromstring(xml_str)
        # 遍历XML中的所有<p>元素
        for p_element in root.findall(".//p"):
            # 获取文本内容和时间属性
            text = p_element.text
            time = int(p_element.get("t"))
            duration = int(p_element.get("d"))

            yield __find_pwd(text)


def get_pwd(url: str, by_ocr: bool) -> str:
    """
    获取候选密码列表
    :param url: YouTube 视频链接
    :param by_ocr: 是否通过 ocr
    :return: 候选密码
    """
    # 创建 YouTube 对象
    yt = pytube.YouTube(url)
    print(f"访问 {url}")

    # 获取视频流
    stream: pytube.Stream
    for opt in ["360p", "480p", "720p"]:
        stream = yt.streams.get_by_resolution(opt)
        if stream:
            print(f"获取视频流 {opt}")
            break

    if by_ocr:
        # 调用ocr获得密码
        apicaller = APICaller()  # apicaller 实例
        cap = cv2.VideoCapture(stream.url)  # VideoCapture 实例获取截图
        for frame in __get_frame(cap):
            yield from (pwd for pwd in _get_pwd_by_ocr(apicaller, frame) if pwd)

        cap.release()  # 释放视频捕获对象
    else:
        # 通过字幕获取密码
        subtitles = yt.captions.all()
        yield from (pwd for pwd in _get_pwd_from_caption(subtitles) if pwd)


if __name__ == "__main__":
    # test
    link_urls = [("https://youtu.be/ZUSNmlndeR8", False), ("https://youtu.be/bYEbmGSBsi8", True)]

    for PWD in get_pwd(*link_urls[1]):
        print(PWD)