# -*- encoding: utf-8 -*-
'''
@author: Great God
'''
from socket import *
import struct
import time

class TcpClient:
    def __init__(self):
        self.BUFSIZ = 1024
        self.ADDR = ('127.0.0.1', 9898)
        self.client=socket(AF_INET, SOCK_STREAM)
        self.client.connect(self.ADDR)
        self.client.settimeout(1)

    def Send(self):

        recv_stat = 'put {"task_name":"test01","config":"test.conf"}'
        self.client.send(str(recv_stat).encode())
        data = self.client.recv(self.BUFSIZ)
        if data:
            print(data.decode())

        time.sleep(5)
        recv_stat = 'set state starte task_name test01'
        self.client.send(str(recv_stat).encode())
        data = self.client.recv(self.BUFSIZ)
        if data:
            print(data.decode())

        for i in range(10):
            time.sleep(1)
        self.client.close()

    def close(self):
        self.client.close()

TcpClient().Send()