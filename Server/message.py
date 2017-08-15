# coding=utf-8

import os
import sys
import codecs
import json
import logging
import logging.config
from rpyc import Service
from rpyc.utils.server import ThreadedServer
from ConfigParser import SafeConfigParser

__author__ = u"AlvinYuan"


class Message(Service):
    @staticmethod
    def exposed_send(message):
        import urllib2

        logger.info(u"短信内容：" + message)

        lx = u"0"
        dlzh = cf.get(u"message", u"username")
        dlmm = cf.get(u"message", u"password")
        sjhm = cf.get(u"message", u"phone")
        url = cf.get(u"message", u"url")
        dxnr = urllib2.quote(message.encode(u"GB18030"))
        fhls = u"0"
        data = u"LX=" + lx + u"&DLZH=" + dlzh + u"&DLMM=" + dlmm + u"&SJHM=" + sjhm + u"&DXNR=" + dxnr + u"&FHLS=" + fhls
        url = url + data
        request = urllib2.Request(url)
        response = urllib2.urlopen(request).read()
        response = response.decode(u"GB18030")
        if response == u"0":
            logger.info(u"警报短信发送成功！")
        else:
            logger.warning(u"警报短信发送失败，返回码：" + response)

        return response


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


def read_conf(path=u"message.conf"):
    """
    加载配置
    :param path: 配置文件路径
    :return: ConfigParser
    """
    if not os.path.exists(path):
        logger.error(u"没有找到配置文件：\"message.conf\" ！")
        sys.exit(2)

    config = SafeConfigParser()
    with codecs.open(path, u"rb", encoding=u"utf8") as c_file:
        config.readfp(c_file)

    return config


if __name__ == u'__main__':
    # 系统文件分隔符
    sep = os.sep
    # 脚本当前所在路径，用GB18030解码以解决中文路径问题
    c_path = os.path.split(os.path.realpath(__file__))[0].decode(u"GB18030")
    # 加载日志配置
    setup_logging(path=os.path.join(c_path, u"config/message.json"))
    logger = logging.getLogger(__name__)
    # 加载配置文件
    config_file = os.path.join(c_path, u"config/message.conf")
    cf = read_conf(path=config_file)

    service = ThreadedServer(Message, port=9999, auto_register=False)
    service.start()
