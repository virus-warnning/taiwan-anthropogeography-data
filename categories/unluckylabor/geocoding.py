#!../../../bin/python
# coding: utf-8

import os
import sys
 
commons_path = os.path.realpath('../../commons')
sys.path.insert(1, commons_path)

import corp_utils
import smart_dbapi

LIMIT = 5

sql  = 'SELECT id,corperation FROM unluckylabor WHERE lat=0.0 AND lng=0.0 LIMIT ?'
conn = smart_dbapi.connect('unluckylabor.sqlite')
curr = conn.execute(sql, (LIMIT,))
for row in curr:
	point = corp_utils.get_corp_location(row['corperation'])
	if point != False:
		conn.execute('UPDATE unluckylabor SET lat=?, lng=? WHERE id=?', (point[0], point[1], row['id']))
		conn.commit()
conn.close()