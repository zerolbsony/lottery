# -*- coding:utf-8 -*-
import threading
import time
import MySQLdb
#import sys
conn=MySQLdb.connect(host='localhost',user='root',passwd='',port=3306,charset='utf8')
db=conn.cursor()
conn.select_db('lottery')
result = db.execute('update lottery set amount=amount-1, updated=unix_timestamp(now()) where id = 1 and amount>=1')
print bytes(result)
if(result):
    rs = conn.commit()
    print bytes(rs)
