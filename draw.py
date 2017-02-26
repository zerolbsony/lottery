# -*- coding:utf-8 -*-
import threading
import time
import MySQLdb

conn=MySQLdb.connect(host='localhost',user='root',passwd='',port=3306)
db=conn.cursor()
conn.select_db('lottery')

def action(arg):
    time.sleep(1)
    #print  'sub thread start!the thread name is:%s\r' % threading.currentThread().getName()
    #print 'the arg is:%s\r' %arg
    uname = threading.currentThread().getName()
    id = 1
    draw(id, uname)
    time.sleep(1)

def draw(id, uname):
    result = lock(id)
    print uname + ', lock result is ' + bytes(result)
    if(result):
        data = {'uname': uname, 'lottery_id': id}
        result = record(data)
        print uname + ', record result is ' + bytes(result)

#锁库存表
def lock(id):
    try:
        id = bytes(id)
        result = db.execute('update lottery set amount=amount-1, updated=unix_timestamp(now()) where id = '+id+' and amount>=1')
        if(result):
            conn.commit()
        return result
    except:
            db.rollback()
            return false

#记录抽奖记录
def record(data):
    try:
        result = db.execute("insert into lottery_record (uname, lottery_id, created) values ('%s', %d, unix_timestamp(now()))", data['uname'], data['lottery_id'])
        if(result):
            conn.commit()
        return result
    except:
        db.rollback()
        return false

users = ['黄厚生','郭巍','熊炜','陈锡乾','张梅珍','夏增明','陈敏章','徐亮'];
#users = ['黄厚生','郭巍','熊炜','陈锡乾','张梅珍','夏增明','陈敏章','徐亮','陈德俊','朱磊','杨锐鹏','柯学','邓小华','李珉','郭春明','李金山','未写名','谢宏','章蛮','高平','好心人','时晶','林起泰'];

for i in xrange(len(users)):
    t =threading.Thread(target=action,args=(users[i],))
    t.start()

print 'main_thread end!'
#db.close()
#conn.close()
