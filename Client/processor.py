# coding=utf-8
import shutil
import socket
import logging
import re
import tarfile
import time
import os
from datetime import datetime
import paramiko
from rpyc import Service
import getpass
from psutil import disk_usage

__author__ = "AlvinYuan"


class Processor(Service):
    def __init__(self, c_path, cf, ip, system, conn):
        super(Processor, self).__init__(conn)
        self._conn = conn
        self.c_path = c_path
        self.cf = cf
        self.ip = ip
        self.system = system
        self.logger = logging.getLogger(__name__)
        self.sep = os.sep
        self.user = getpass.getuser()

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

    def exposed_collect(self):
        self.logger.info(u"=" * 20)
        self.logger.info(u"收到服务器请求，开始备份日志 ……")

        f_dic = find()
        tar_dic = compress(f_dic, self.c_path + self.sep)
        upload(tar_dic)

        self.logger.info(u"开始删除旧日志 ……")
        delete(f_dic)
        self.logger.info(u"开始删除本地备份文件 ……")
        delete(tar_dic)

        self.logger.info(u"备份完毕！")
