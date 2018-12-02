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
        data=self.client.recv(self.BUFSIZ)
        recv_stat = {'a':'1'}
        self.client.send(str(recv_stat).encode())
        if data:
            a = data.read()
            print(a)

    def close(self):
        self.client.close()

TcpClient().Send()