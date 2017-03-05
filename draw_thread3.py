# -*- coding:utf-8 -*-
import threading
import time
import MySQLdb
import sys
import redis
import random

'''
要满足商品库存不会成负数都前提下，中奖记录也不会记录多发
'''

redis_client = redis.StrictRedis(host='127.0.0.1', port=6379)
lottery_left_key = '1_left'
redis_client.set(lottery_left_key, 2)

class MyThread(threading.Thread):
    def __init__(self,arg):
        super(MyThread, self).__init__()#注意：一定要显式的调用父类的初始化函数。
        self.arg = arg
        self.conn=MySQLdb.connect(host='localhost',user='root',passwd='',port=3306,charset='utf8')
        self.db=self.conn.cursor()
        self.conn.select_db('lottery')

        self.redis = redis.StrictRedis(host='127.0.0.1', port=6379)
        self.lottery_left_key = '1_left'

    def run(self):#定义每个线程要运行的函数
        time.sleep(1)
        uname = self.arg
        id = 1
        self.draw(id, uname)

    def draw(self, id, uname):
        key = 'draw_'+bytes(id)+'_number_'
	lock_key = self.lottery_left_key+'_lock'
	lock_key_rs = self.redis.setex(lock_key, 5, uname)
	print 'lock_key is ' + lock_key + ', lock_key_rs is ' + bytes(lock_key_rs)
        left = self.redis.get(self.lottery_left_key)
        left = int(left)
	print 'left is ' + bytes(left)
        if(left > 0 and lock_key_rs):
            lock_rs = self.redis.setex(key+bytes(left), 5, uname)
	    print 'key is ' + key + bytes(left) + ', lock_rs is ' + bytes(lock_rs)
            if(lock_rs):
                result = self.lock(id)
                print uname + ', lock result is ' + bytes(result)

                data = {'uname': uname, 'lottery_id': id}
		if(result):
		    result = self.record(data)
		    print uname + ', record result is ' + bytes(result)
		    '''
		    if(result):
			data = {'uname': uname, 'lottery_id': id}
			result = self.record(data)
			print uname + ', record result is ' + bytes(result)
		    '''

    #锁库存表
    def lock(self, id):
        try:
            id = bytes(id)
            #print 'update lottery set amount=amount-1, updated=unix_timestamp(now()) where id = '+id+' and amount>=1'
            result = self.db.execute('update lottery set amount=amount-1, updated=unix_timestamp(now()) where id = '+id+' and amount>=1')
            if(result):
                self.conn.commit()
	    self.redis.decr(self.lottery_left_key)
	    lock_key = self.lottery_left_key+'_lock'
	    self.redis.delete(lock_key)
            print 'decr is '+bytes(self.redis.get(self.lottery_left_key))
            return result
        except:
            self.conn.rollback()
            return 0

    #记录抽奖记录
    def record(self, data):
        try:
            print "insert into lottery_record (uname, lottery_id, created) values ('"+data['uname']+"', "+bytes(data['lottery_id'])+", unix_timestamp(now()))"
            result = self.db.execute("insert into lottery_record (uname, lottery_id, created) values ('"+data['uname']+"', "+bytes(data['lottery_id'])+", unix_timestamp(now()))")
            if(result):
                self.conn.commit()
            return 1
        except:
            print "rollback, insert into lottery_record (uname, lottery_id, created) values ('"+data['uname']+"', "+bytes(data['lottery_id'])+", unix_timestamp(now()))"
            self.conn.rollback()
            return 0

#users = ['黄厚生','郭巍','熊炜','陈锡乾'];
#users = ['黄厚生','郭巍','熊炜','陈锡乾','张梅珍','夏增明','陈敏章','徐亮'];
users = ['黄厚生','郭巍','熊炜','陈锡乾','张梅珍','夏增明','陈敏章','徐亮','陈德俊','朱磊','杨锐鹏','柯学','邓小华','李珉','郭春明','李金山','未写名','谢宏','章蛮','高平','好心人','时晶','林起泰'];
#random.shuffle(users)

for i in xrange(len(users)):
    '''
    self.conn=MySQLdb.connect(host='localhost',user='root',passwd='',port=3306,charset='utf8')
    self.db=self.conn.cursor()
    self.conn.select_db('lottery')
    '''
    t = MyThread(users[i])
    t.start()

print 'main_thread end!'

#time.sleep(10)
#self.db.close()
#self.conn.close()
