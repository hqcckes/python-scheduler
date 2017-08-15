# coding=utf-8

import getpass
import locale
import shutil
import socket
import tarfile
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
import paramiko
import rpyc
from datetime import datetime
from rpyc import Service
from rpyc.utils.server import ThreadedServer
from psutil import disk_usage

__author__ = u"AlvinYuan"


class Client(Service):
    @staticmethod
    def exposed_check():
        logger.info(u"收到服务器请求，开始检查磁盘空间 ……")
        drives = set()
        index = 0 if system == u"Windows" else 1
        path_dic = get_path()
        for key, values in path_dic.items():
            for value in values:
                drive = value.replace(sep, u"/").split(u"/")[index]
                drives.add(drive if system == u"Windows" else u"/" + drive)

        threshold = get_client_conf(u"threshold")
        for drive in drives:
            usage = disk_usage(drive).percent
            logger.info(u"磁盘使用率 --- " + drive + u" ==> " + unicode(usage) + u"%")
            if usage >= threshold:
                return True

        return False

    @staticmethod
    def exposed_collect():
        logger.info(u"=" * 20)
        logger.info(u"收到服务器请求，开始备份日志 ……")

        f_dic = find()
        if f_dic is None:
            logger.warning(u"取消备份 ……")
            return False

        tar_dic = compress(f_dic, c_path + sep)
        if tar_dic is None:
            logger.warning(u"取消备份 ……")
            return False

        if not upload(tar_dic):
            logger.warning(u"取消备份 ……")
            return False

        logger.info(u"开始删除旧日志 ……")
        delete(f_dic)
        logger.info(u"开始删除本地备份文件 ……")
        delete(tar_dic)

        logger.info(u"备份完毕！")
        return True


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


def get_conn():
    if connection is not None:
        return

    hostname = get_client_conf(u"hostname")
    monitor_port = get_client_conf(u"monitor_port")
    while True:
        try:
            logger.info(u"与服务器建立连接 ……")
            conn = rpyc.connect(hostname, int(monitor_port))
            logger.info(u"连接成功！")
            return conn
        except socket.error as se:
            logger.error(u"无法连接到服务器：" + hostname + u":" + monitor_port + u"，一分钟后重试 ……")
            logger.error(se, exc_info=True)
            time.sleep(60)


def get_client_conf(key):
    return cf.get(u"client", key)


def send(message):
    logger.info(u"开始发送警报短信 ……")
    message = u"[" + ip + u"] - " + message + u" - " + time.strftime(u"%Y-%m-%d %H:%M:%S", time.localtime())

    logger.info(u"短信内容：" + message)

    try:
        rs = connection.root.send(message)
        logger.info(rs)

        if rs == u"0":
            logger.info(u"警报短信发送成功！")
        else:
            logger.warning(u"警报短信发送失败，返回码：" + rs)
    except EOFError as e:
        logger.error(u"警报短信发送失败！", exc_info=True)


def get_path():
    path = get_client_conf(u"path")
    s_list = path.split(u";")
    dic = {}
    for s in s_list:
        sp = s.split(u"|")
        if len(sp) != 2:
            send(u"【错误】日志备份失败：配置项\"[client] - path\"有误！")

        key = sp[0]
        value = sp[1]
        if key in dic:
            lst = dic[key]
            if value not in lst:
                lst.append(value)

            dic[key] = lst
        else:
            dic[key] = [value]

    return dic


def search(path, pattern):
    all_files = os.listdir(path)
    f_list = []
    for f in all_files:
        if os.path.isdir(path + sep + f):
            if pattern is None:
                return True
            else:
                p = re.compile(pattern)
                m = p.match(f)
                if m:
                    flag = True
                else:
                    flag = False

            if flag:
                f_list.append(path + sep + f)

    return f_list


def find():
    logger.info(u"开始查找要备份的日志 ……")
    f_dic = {}
    pattern = u"\d{4}-\d{2}-\d{2}"
    path_dic = get_path()
    for key, paths in path_dic.items():
        for path in paths:
            if not os.path.exists(path):
                send(u"【错误】 不能开始备份，路径\"" + path + u"\"不存在！")

            lst = search(path=path, pattern=pattern)
            if not lst:
                logger.warning(path + u"：没有找到要备份的日志！")
                continue

            l = len(lst)
            if l <= 10:
                logger.warning(path + u"：只有" + unicode(l) + u"天的日志，不需要备份！")
                continue

            lst.sort(reverse=True)
            lst = lst[10:]
            lst.sort()

            if key in f_dic:
                tmp_list = f_dic[key]
                tmp_list.extend(lst)
            else:
                f_dic[key] = lst

            logger.info(path + u"：查找完毕！")

    if not f_dic:
        send(u"没有找到任何需要备份的日志！")
        return None

    logger.info(u"日志查找完毕！")
    return f_dic


def compress(f_dic, target):
    logger.info(u"开始压缩日志 ……")
    tar_dic = {}

    prefix = getpass.getuser() + u"_" + ip + u"_"
    for key, value in f_dic.items():
        start = value[0].split(sep)[-1]
        end = value[-1].split(sep)[-1]
        name = prefix + key + u"_" + start + u"_" + end + u".tar.gz"
        backup = target + name

        if os.path.exists(backup):
            timestamp = datetime.now().strftime(u"%Y%m%d%H%M%S%f")
            os.rename(backup, backup + u"." + timestamp + u".bak")

        try:
            tar = tarfile.open(backup, u"w:gz")
        except (ValueError, tarfile.ReadError, tarfile.CompressionError) as e:
            logger.error(e, exc_info=True)
            send(u"【错误】日志备份失败：文件\"" + name + u"\"压缩失败！")
            return None

    logger.info(u"日志压缩完毕！")
    return tar_dic


def upload(tar_dic):
    logger.info(u"开始上传日志文件 ……")
    try:
        transport = paramiko.Transport(
            sock=socket.create_connection((get_client_conf(u"hostname"), int(get_client_conf(u"port"))),
                                          timeout=None))
        transport.connect(username=get_client_conf(u"username"), password=get_client_conf(u"password"))
        sftp = paramiko.SFTPClient.from_transport(transport)

        backup_dir = get_client_conf(u"backup_dir")
        for key, value in tar_dic.items():
            for f in value:
                name = f.replace(sep, u"/").strip(u"/").split(u"/")[-1]
                sftp.put(localpath=f, remotepath=backup_dir + u"/" + name)
                logger.info(name + u"：上传成功！")

        sftp.close()
        transport.close()

        logger.info(u"日志上传完毕！")
        return True
    except (paramiko.SSHException, socket.error) as e:
        logger.error(e, exc_info=True)
        send(u"【错误】日志备份失败：文件上传失败！")
        return False


def delete(dic):
    for key, value in dic.items():
        for f in value:
            name = key + u"：" + f.replace(sep, u"/").strip(u"/").split(u"/")[-1]
            try:
                if os.path.isdir(f):
                    shutil.rmtree(f)
                elif os.path.isfile(f):
                    os.remove(f)

                logger.info(name + u"：删除成功！")
            except OSError:
                logger.warning(name + u"：删除失败！")


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
    connection = None
    connection = get_conn()

    service = ThreadedServer(Client, port=9999, auto_register=False)
    service.start()
