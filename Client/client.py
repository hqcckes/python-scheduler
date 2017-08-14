# coding=utf-8
import locale
import socket
from ConfigParser import SafeConfigParser
import codecs
import json
import logging.config
import os
import sys
import subprocess
import time
import platform
import re

import rpyc
from rpyc import Service
from processor import Processor

__author__ = u"AlvinYuan"


class Client(Service):
    @staticmethod
    def exposed_check():
        """
        检查磁盘空间
        :return:
        """
        pass


def setup_logging(path=u"logging.json", level=logging.INFO, env_key=u"LOG_CFG"):
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


def read_conf(path=u"client.conf"):
    """
    加载配置
    :param path: 配置文件路径
    :return: ConfigParser
    """
    if not os.path.exists(path):
        logger.error(u"没有找到配置文件：\"client.conf\" ！")
        sys.exit(2)

    config = SafeConfigParser()
    with codecs.open(path, u"rb", encoding=u"utf8") as c_file:
        config.readfp(c_file)

    return config


def get_ip():
    ip_str = u"([0-9]{1,3}.){3}[0-9]{1,3}"
    if system == u"Darwin" or system == u"Linux":
        ipconfig_process = subprocess.Popen(u"ifconfig", stdout=subprocess.PIPE)
        output = ipconfig_process.stdout.read()
        ip_pattern = u"(inet " + ip_str + u")"
        if system == u"Linux":
            ip_pattern = u"(inet addr:" + ip_str + u")"
        ip_pattern = re.compile(ip_pattern)
    else:
        code = locale.getdefaultlocale()[1]
        ipconfig_process = subprocess.Popen(u"ipconfig", stdout=subprocess.PIPE)
        output = ipconfig_process.stdout.read().decode(code)
        if code == u"cp936":
            ip_pattern = u"IPv4 地址[. ]*: " + ip_str
        else:
            ip_pattern = u"IPv4 Address[. ]*: " + ip_str

    ip_pattern = re.compile(ip_pattern)
    pattern = re.compile(ip_str)
    ip_list = []
    for i in re.finditer(ip_pattern, unicode(output)):
        i = pattern.search(i.group())
        if i.group() != u"127.0.0.1":
            ip_list.append(i.group())

    if not ip_list:
        return None

    return ip_list


if __name__ == u'__main__':
    # 系统文件分隔符
    sep = os.sep
    # 脚本当前所在路径，用GB18030解码以解决中文路径问题
    c_path = os.path.split(os.path.realpath(__file__))[0].decode(u"GB18030")
    # 加载日志配置
    setup_logging(path=os.path.join(c_path, u"config/logging.json"))
    logger = logging.getLogger(__name__)
    # 加载配置文件
    config_file = os.path.join(c_path, u"config/client.conf")
    cf = read_conf(path=config_file)
    # 获取本机ip
    system = platform.system()
    ip = get_ip()
    ip = u"" if not ip else ip[0]

    # 获取服务器连接

    processor = Processor(cf=cf, ip=ip, system=system)
    processor.get_conn()
