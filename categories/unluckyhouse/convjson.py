#!../../../bin/python
# coding: utf-8

import os
import sys
import geojson

commons_path = os.path.realpath('../../commons')
sys.path.insert(1, commons_path)

import smart_dbapi

sql = 'SELECT * FROM unluckyhouse WHERE state>1 ORDER BY id DESC'
con = smart_dbapi.connect('unluckyhouse.sqlite')
cur = con.execute(sql)

# 死法代碼對應文字
INITATIVE_TAGS = {"A": u"意外", "S": u"自殺", "M": u"他殺"}

features = []
for row in cur:
	point = geojson.Point((row['lng'], row['lat']))
	properties = {
		'id': row['id'],
		'news': row['news'],
		'datetime': row['datetime'],
		'address': row['area'] + row['address'],
		'approach': '%s %s' % (INITATIVE_TAGS[row['initative']], row['approach']),
		'marker-color': '#b00000',
		'marker-symbol': 'danger'
	}

	features.append(geojson.Feature(geometry=point, properties=properties))

cur.close()
con.close()

fc = geojson.FeatureCollection(features)
print(geojson.dumps(fc, indent=2))
