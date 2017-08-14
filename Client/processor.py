# coding=utf-8

__author__ = "AlvinYuan"

import socket
import logging
import re
import time
import os
import rpyc
from psutil import disk_usage


class Processor:
    def __init__(self, cf, ip, system):
        self.cf = cf
        self.ip = ip
        self.system = system
        self.conn = None
        self.logger = logging.getLogger(__name__)
        self.sep = os.sep

    def get_client_conf(self, key):
        return self.cf.get(u"client", key)

    def get_conn(self):
        if self.conn is not None:
            return

        hostname = self.get_client_conf(u"hostname")
        monitor_port = self.get_client_conf(u"monitor_port")
        while True:
            try:
                self.logger.info(u"与服务器建立连接 ……")
                self.conn = rpyc.connect(hostname, int(monitor_port))
                self.logger.info(u"连接成功！")
                return
            except socket.error as se:
                self.logger.error(u"无法连接到服务器：" + hostname + u":" + monitor_port + u"，一分钟后重试 ……")
                self.logger.error(se, exc_info=True)
                time.sleep(60)

    def send(self, message):
        self.logger.info(u"开始发送警报短信 ……")
        message = u"[" + self.ip + u"] - " + message + u" - " + time.strftime(u"%Y-%m-%d %H:%M:%S", time.localtime())
        pass

    def get_path(self):
        path = self.get_client_conf(u"path")
        s_list = path.split(u";")
        dic = {}
        for s in s_list:
            sp = s.split(u"|")
            if len(sp) != 2:
                self.send(u"【错误】日志备份失败：配置项\"[client] - path\"有误！")

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

    def search(self, path, pattern):
        all_files = os.listdir(path)
        f_list = []
        for f in all_files:
            if os.path.isdir(path + self.sep + f):
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
                    f_list.append(path + self.sep + f)

        return f_list

    def find(self):
        self.logger.info(u"开始查找要备份的日志 ……")
        f_dic = {}
        pattern = u"\d{4}-\d{2}-\d{2}"
        path_dic = self.get_path()
        for key, paths in path_dic.items():
            for path in paths:
                if not os.path.exists(path):
                    self.send(u"【错误】 不能开始备份，路径\"" + path + u"\"不存在！")

    def exposed_check(self):
        self.logger.info(u"收到服务器请求，开始检查磁盘空间 ……")
        drives = set()
        index = 0 if self.system == u"Windows" else 1
        path_dic = self.get_path()
        for key, values in path_dic.items():
            for value in values:
                drive = value.replace(self.sep, u"/").split(u"/")[index]
                drives.add(drive if self.system == u"Windows" else u"/" + drive)

        dic = {}
        threshold = self.get_client_conf(u"threshold")
        for drive in drives:
            usage = disk_usage(drive).percent
            self.logger.info(u"磁盘使用率 --- " + drive + u" ==> " + unicode(usage) + u"%")
            dic[drive] = usage

        return [threshold, dic]
