# -*- encoding: utf-8 -*-
'''
@author: xiaozhong
'''
import time
from zk_handle.zkHandler import zkHander
from contextlib import closing
from lib.get_conf import GetConf
from lib.System import Replace
from db_handle.dbHandle import dbHandle
from lib.SendRoute import SendRoute
import logging
logging.basicConfig(filename='mha_server.log',
                    level=logging.INFO,
                    format  = '%(asctime)s  %(filename)s : %(levelname)s  %(message)s',
                    datefmt='%Y-%m-%d %A %H:%M:%S')

class SlaveCheck:
    def __init__(self,zkhander=None):
        self.online_node = GetConf().GetOnlinePath()
        self.slave_down_path = GetConf().GetSlaveDown()
        self.zkhander = zkhander
    """检查是否在线"""
    def CheckOnline(self,proxy_value,groupname):
        slave_list = eval(proxy_value['read'])

        for h in slave_list:
            if h != proxy_value['write']:       #去除master节点的检查，master节点有watch
                __host,__port = h.split(':')[0],h.split(':')[1]
                status = self.zkhander.Exists('{}/{}'.format(self.online_node,Replace(__host)))
                if status is None:
                    logging.warning('This Group Server {} has slave node:{} is down '.format(groupname, __host))
                    __status = self.zkhander.Exists('{}/{}'.format(self.slave_down_path,Replace(__host)))
                    if __status is None:
                        self.zkhander.Create(path='{}/{}'.format(self.slave_down_path,Replace(__host)), value=str({'groupname':groupname,'port':__port}),seq=False)              #slave节点不在线创建slavedown节点
                    else:
                        logging.warning('This host:{} outage task is being '.format(__host))

    """获取haproxy状态信息进行slave筛选"""
    def WhileCheckSLave(self):
        ha_list = self.zkhander.GetHaChildren()
        for ha in ha_list:
            proxy_value = self.zkhander.GetHaproxy(groupname=ha)
            self.CheckOnline(proxy_value,ha)

    """操作slave节点的状态信息"""
    def StaticInfo(self,result,host):
        with closing(zkHander()) as zkhander:
            online_state = zkhander.Exists('{}/{}'.format(self.online_node,host))
            if online_state is None:
                port,groupname = result['port'],result['groupname']
                for i in range(0,3):
                    with closing(dbHandle(Replace(host), port)) as dbhandle:
                        mysqlstate = dbhandle.RetryConn()  # 检测mysql是否能正常连接
                    time.sleep(1)
                if mysqlstate:
                    zkhander.DeleteSlaveDown(host)
                    logging.warning('Groupname:{} slave host:{} is online,but python client server is not online!'.format(groupname,Replace(host)))
                else:
                    lock_state = zkhander.SetLockTask(host)
                    if lock_state:
                        alter_state = self.AlterHaproxy(groupname=groupname,delete_host=Replace(host),port=port)
                        if alter_state:
                            zkhander.DeleteSlaveDown(host)
                            zkhander.DeleteLockTask(host)
                        else:
                            zkhander.DeleteLockTask(host)
                    else:
                        logging.warning('slave:{} outage task  elsewhere in the execution'.format(Replace(host)))
            else:
                zkhander.DeleteSlaveDown(host)

    """修改路由状态"""
    def AlterHaproxy(self,groupname,delete_host,port):
        delete_host_str = '{}:{}'.format(delete_host,port)
        with closing(zkHander()) as zkhander:
            result = zkhander.GetHaproxy(groupname=groupname)
            read_list = eval(result['read'])
            if delete_host_str in read_list:
                read_list.remove(delete_host_str)       #删除宕机slave节点
            zkhander.SetHaproxyMeta(group=groupname,reads=read_list,master=result['write'],type=1)
            return SendRoute(group_name=groupname)

"""离线slave节点操作函数"""
def ManageDownNode(host):
    slave_down_path = GetConf().GetSlaveDown()
    with closing(zkHander()) as zkhander:
        result = zkhander.Get(path='{}/{}'.format(slave_down_path,host))
        SlaveCheck().StaticInfo(result=eval(result),host=host)


def SlaveDownCheck():
    with closing(zkHander()) as zkhander:
        downlist = zkhander.GetDownSlaveList()
        if downlist:
            for host in downlist:
                ManageDownNode(host=host)

def Run():
    SlaveDownCheck() #检查是否有已存在的宕机节点
    zkHander().CreateChildrenWatch(path=GetConf().GetSlaveDown(),func=ManageDownNode)

    with closing(zkHander()) as zkhander:
        while True:
            SlaveCheck(zkhander).WhileCheckSLave()
            time.sleep(3)           #每3秒扫描一次slave在线状态