# -*- coding:utf-8 -*-
import threading
import time
import MySQLdb
import sys
import redis
import random

'''
要满足商品库存不会成负数都前提下，中奖记录也不会记录多发，同时考虑加锁后，执行操作超时，有部分操作成功，部分操作待执行的情况，该怎么处理
1>如果在减少库存时超时,这是锁被释放,机会留给了别人
2>如果减少库存成功后超时,锁被释放,但是这个机会应该还是当前用户的,需要将中奖纪录补上。因为下一个人拿到锁但是库存已经没有了,但这里要保证redis和db的库存个数保持一致性
3>如果减少库存成功,但是写入中奖纪录数据执行失败或由于进程被中断导致没有执行。该怎么处理
当库存成功-1时,可以认定为用户已中奖,不过如果
'''

redis_client = redis.StrictRedis(host='127.0.0.1', port=6379)
lottery_left_key = '2_left'#这里后续需要做成动态@todo
#这里后续需要做成动态@todo
redis_client.set(lottery_left_key, 1)#这里要考虑设置过期时间,因为如果计数和db保持不了一致性时,通过过期后再从db读一遍就没问题了。所以db一定要保证计数没问题,不会超

class MyThread(threading.Thread):
    def __init__(self,arg):
        super(MyThread, self).__init__()#注意：一定要显式的调用父类的初始化函数。
        self.arg = arg
        self.conn=MySQLdb.connect(host='localhost',user='root',passwd='',port=3306,charset='utf8')
        self.db=self.conn.cursor()
        self.conn.select_db('lottery')

        self.redis = redis.StrictRedis(host='127.0.0.1', port=6379)
        self.lottery_left_key = '2_left'#这里后续需要做成动态@todo

    def run(self):#定义每个线程要运行的函数
        time.sleep(1)
        uname = self.arg
        id = 2#这里后续需要做成动态@todo
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
            #if(uname == '黄厚生'):
            #    time.sleep(10) #这里故意超时,为了能够让锁超时被释放,然后机会就让给了另外一个线程(超时时间是5秒,这里睡10秒) 这是上面说的第一种情况
            lock_rs = self.redis.setex(key+bytes(left), 5, uname)#作用不大，如果用户中不了奖，还得将这个锁释放
            print 'key is ' + key + bytes(left) + ', lock_rs is ' + bytes(lock_rs)
            if(lock_rs):
                #这里可以采用先纪录log日志(最好是保存到db中),标记uname操作减少的该id对应的奖品的库存,以便查问题
                #log(uname+' lock lottery table, status is ready, logid is 唯一识别号') @todo
                result = self.lock(id, uname)
                print uname + ', lock result is ' + bytes(result)
                #@todo 【key+bytes(left) 这个key有效期只有5秒的情况】 假如在执行下面代码前进程就中断了，那可以通过分析日志是否存在不成对的，找出并看下其对应的lock操作是否成功，如果成功，将中奖记录补一下。如果找不到该用户的lock操作的日志的话,那就默认为成功。
                #@todo 【key+bytes(left) 这个key有效期1小时或1天的情况】 假如在执行下面代码前进程就中断了，可以根据redis里纪录的中奖用户信息,将中奖纪录补录到表中,因为这个key可以在填完中奖纪录后删掉,如果存在这个key，就代表中奖记录没有写入成功。
                #log(uname+' lock lottery table, status is '+(result)?'ok':'fail'+', logid is 唯一识别号') @todo当遇到上面说的第三种情况时,这里已经知道成功了,那可以将这个用户的中奖纪录补一下
                data = {'uname': uname, 'lottery_id': id}
		if(result):
		    result = self.record(data)#中奖纪录写入失败要有重试机制@todo
		    print uname + ', record result is ' + bytes(result)
		    '''
		    if(result):
			data = {'uname': uname, 'lottery_id': id}
			result = self.record(data)
			print uname + ', record result is ' + bytes(result)
		    '''

    #锁库存表
    def lock(self, id, uname):
        try:
            id = bytes(id)
            #print 'update lottery set amount=amount-1, updated=unix_timestamp(now()) where id = '+id+' and amount>=1'
            result = self.db.execute('update lottery set amount=amount-1, updated=unix_timestamp(now()) where id = '+id+' and amount>=1')
            if(result):
                self.conn.commit()
                if(uname == '黄厚生'):
                    time.sleep(10)#这是上面说的第二种情况
                self.redis.decr(self.lottery_left_key)#这里要保证如果失败会重试@todo
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

users = ['黄厚生','郭巍'];
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
