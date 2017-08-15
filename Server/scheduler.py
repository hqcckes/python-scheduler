# coding=utf-8

import codecs
import json
import logging
import logging.config
import os
import platform
import socket

import rpyc

__author__ = "AlvinYuan"


def setup_logging(path=u"message.json", level=logging.INFO, env_key=u"LOG_CFG"):
    """
    加载日志配置
    :param path: 默认路径
    :param level: 默认日志等级
    :param env_key: 环境变量
    :return:
    """
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with codecs.open(filename=path, mode=u"rb", encoding=u"utf8") as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=level)


def get_clients(path):
    if not os.path.exists(path):
        logger.error(u"找不到保存有服务器信息的文件！")

    with codecs.open(path, u"rb", encoding=u"utf8") as servers:
        lst = servers.readlines()

    return lst


def clear_window():
    if system == u"Windows":
        os.system(u"cls")
    else:
        os.system(u"clear")


def check_disk(lst):
    dic = {}
    for s in lst:
        s = s.strip()
        try:
            conn = rpyc.connect(host=s, port=9999)
            dic[s] = conn.root.check()
            conn.close()
        except socket.error as e:
            logger.error(u"无法连接到服务器：" + s + u":9999")
            logger.error(e, exc_info=True)
            continue
        finally:
            conn.close()

    return dic


if __name__ == u'__main__':
    # 清屏
    system = platform.system()
    clear_window()
    # 系统文件分隔符
    sep = os.sep
    # 脚本当前所在路径，用GB18030解码以解决中文路径问题
    c_path = os.path.split(os.path.realpath(__file__))[0].decode(u"GB18030")
    # 加载日志配置
    setup_logging(path=os.path.join(c_path, u"config/message.json"))
    logger = logging.getLogger(__name__)
    # 加载服务器列表
    s_path = os.path.join(c_path, u"config/servers.list")
    s_list = get_clients(s_path)

    # 检查磁盘空间
    rs_dic = check_disk(s_list)
    print rs_dic
