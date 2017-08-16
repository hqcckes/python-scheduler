# coding=utf-8

import codecs
import json
import logging
import logging.config
import os
import platform
import socket
import rpyc


def setup_logging(path, level=logging.INFO, env_key=u"LOG_CFG"):
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


def get_servers(path):
    if not os.path.exists(path):
        logger.error(u"找不到文件：\"server.list\"")

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
        conn = None
        try:
            conn = rpyc.connect(host=s, port=9999)
            dic[s] = conn.root.check()
        except socket.error as e:
            dic[s] = u"连接失败！"
            logger.error(u"无法连接到服务器：" + s + u":9999")
            logger.error(e, exc_info=True)
        finally:
            if conn is not None:
                conn.close()

        print u'{0}     {1}'.format(s, dic[s])

    return dic


def backup(server):
    conn = None
    try:
        print u"正在" + server + u"上执行备份，请稍后 …… ",
        conn = rpyc.connect(host=server, port=9999)
        rs = conn.root.collect()
        if rs is True:
            print u"备份成功！"
        else:
            print u"备份失败！"
    except socket.error as e:
        print u"备份失败，无法连接到服务器！"
        logger.error(u"无法连接到服务器：" + server + u":9999")
        logger.error(e, exc_info=True)
    finally:
        if conn is not None:
            conn.close()


def get_connected_server(r_dic):
    dic = {}
    for key, value in r_dic.items():
        if value is True or value is False:
            dic[key] = value

    return dic


def get_alert_server(n_dic):
    dic = {}
    for key, value in n_dic.items():
        if value is True:
            dic[key] = value

    return dic


def display_server(o_dic):
    num = 1
    dic = {}
    for key, value in o_dic.items():
        print u'    {0}. {1}     {2}'.format(num, key, value)
        dic[num] = key

    return dic


def single_menu():
    while True:
        clear_window()
        print u"您选择了备份单个服务器，以下是可备份服务器列表："
        s_dic = display_server(nm_dic)
        print
        while True:
            index = raw_input(u"请输入序列号选择一个服务器：")
            try:
                index = int(index)
                server = s_dic[index]
                break
            except (ValueError, KeyError):
                print u"错误：输入有误，请确认你的选择！"
                continue

        confirm = raw_input(u"您选择备份服务器：" + server + u"，请确认（yes/no/exit）：").lower()
        if confirm == u"yes":
            backup(server)
        elif confirm == u"exit":
            break
        else:
            continue


def menu():
    while True:
        clear_window()
        print u"选项："
        print u"    S：备份单个服务器"
        print u"    A: 备份所有可连接的服务器（True/False）"
        print u"    G: 备份使用率超出阈值的服务器（True）"
        print
        print u"    E: 退出"
        print
        option = raw_input(u"请输入选项（S/A/G/E）：").lower()
        print

        if option == u"s":
            single_menu()

            print
            raw_input(u"请输入任意键继续 ……")
            continue
        elif option == u"a":
            display_server(nm_dic)

            print
            raw_input(u"请输入任意键继续 ……")
            continue
        elif option == u"g":
            display_server(al_dic)

            print
            raw_input(u"请输入任意键继续 ……")
            continue
        elif option == u"e":
            break
        else:
            continue


if __name__ == u'__main__':
    # 清屏
    system = platform.system()
    clear_window()
    # 系统文件分隔符
    sep = os.sep
    # 脚本当前所在路径，用GB18030解码以解决中文路径问题
    c_path = os.path.split(os.path.realpath(__file__))[0].decode(u"GB18030")
    # 加载日志配置
    setup_logging(path=os.path.join(c_path, u"config/scheduler.json"))
    logger = logging.getLogger(__name__)
    # 加载服务器列表
    s_path = os.path.join(c_path, u"config/servers.list")
    s_list = get_servers(s_path)

    print u"开始检查服务器磁盘空间，请稍候 ……"
    print
    rs_dic = check_disk(s_list)
    nm_dic = get_connected_server(rs_dic)
    al_dic = get_alert_server(nm_dic)
    print
    menu()
