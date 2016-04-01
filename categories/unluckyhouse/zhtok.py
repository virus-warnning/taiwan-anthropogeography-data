# coding: utf-8

import re
import json
from StringIO import StringIO

# 偵測結果
LCHR_FOUND         = 0 # 找到中文數值
LCHR_NOTFOUND      = 1 # 找不到中文數值
LCHR_MISUNDERSTOOD = 2 # 誤以為有中文數值，但實際上不是

# 中文數值類型
TYPE_DIGITS   = 1 # 純數字
TYPE_SPEAKING = 2 # 朗讀
TYPE_FINANCE  = 3 # 金融
TYPE_XTY      = 4 # 20~49 縮寫
TYPE_YM       = 5 # 元(月/日)

# 中文對應指數
EXP_OF_CHAR = {
	u'兆': 12, u'億': 8, u'萬': 4,
	u'千':  3, u'百': 2, u'十': 1,
	u'仟':  3, u'佰': 2, u'拾': 1
}

## 中文數字轉阿拉伯數字
def convert_arabic_numerals(text):
	strout = StringIO()
	tlen   = len(text)
	offset = 0
	result = detect_value(text, offset)

	while result != False:
		(begin, end, vstr, vtype) = result

		if vtype == TYPE_DIGITS:
			astr = convert_digits_value(vstr)
		elif vtype == TYPE_SPEAKING:
			astr = convert_speaking_value(vstr)
		elif vtype == TYPE_FINANCE:
			astr = convert_finance_value(vstr)
		elif vtype == TYPE_XTY:
			astr = convert_xty_value(vstr)
		elif vtype == TYPE_YM:
			astr = u'1'
		else:
			astr = vstr

		strout.write(text[offset:begin])
		strout.write(astr)
		offset = end

		if offset<tlen and text[offset] == u'兩':
			strout.write(u'兩')
			offset = offset + 1
		
		result = detect_value(text, offset)

	if offset < tlen:
		strout.write(text[offset:])

	ctext = strout.getvalue()
	strout.close()

	return ctext

## 偵測中文內的數值
#
# @param text   內文
# @param offset 偵測起點
#
def detect_value(text, offset = 0):
	end = False

	(result, begin, vtype) = detect_value_prefix(text, offset)
	while result == LCHR_MISUNDERSTOOD:
		(result, begin, vtype) = detect_value_prefix(text, begin + 1)

	if result == LCHR_FOUND:
		if vtype == TYPE_DIGITS:
			end = end_of_digits_value(text, begin)
		elif vtype == TYPE_SPEAKING:
			end = end_of_speaking_value(text, begin)
		elif vtype == TYPE_FINANCE:
			end = end_of_finance_value(text, begin)
		elif vtype == TYPE_XTY:
			end = end_of_xty_value(text, begin)
		elif vtype == TYPE_YM:
			end = begin + 1

	if end == False:
		return False
	else:
		vstr = text[begin:end]

	return (begin, end, vstr, vtype)

## 尋找中文數值的起始字元與判別數值類型
#
# @param text   內文
# @param offset 偵測起點
#
# @return 找到 (LCHR_FOUND, begin, TYPE_XXXX)
#         沒有 (LCHR_NOTFOUND, 0, 0)，不繼續處理
#         誤解 (LCHR_MISUNDERSTOOD, begin, 0)，下次從 begin+1 繼續處理
#
def detect_value_prefix(text, offset = 0):
	# 開頭字元分組，從這裡擴充或停用偵測功能
	categories = (
		u'零〇一二三四五六七八九', # 純數值開頭
		u'兩十',                # 朗讀開頭
		u'壹貳參肆伍陸柒捌玖',   # 金融開頭
		u'廿卅卌',              # 20~49 縮寫開頭
		u'元',                 # 元(月/日)開頭
	)

	pattern = re.compile(u'[%s]' % u''.join(categories))
	m = pattern.search(text, offset)
	if m is None:
		return (LCHR_NOTFOUND, 0, 0)

	ch1   = m.group(0)
	begin = m.start(0)

	# 第一字可識別的數字類型
	# 1.數字：零〇
	# 2.朗讀：兩十
	# 3.金融：壹貳參肆伍陸柒捌玖
	# 4.幾十：廿卅卌
	# 5.年月：元
	if u'零〇'.find(ch1) >= 0:
		return (LCHR_FOUND, begin, TYPE_DIGITS)

	if u'十'.find(ch1) >= 0:
		return (LCHR_FOUND, begin, TYPE_SPEAKING)

	if u'壹貳參肆伍陸柒捌玖'.find(ch1) >= 0:
		return (LCHR_FOUND, begin, TYPE_FINANCE)

	if u'廿卅卌'.find(ch1) >= 0:
		return (LCHR_FOUND, begin, TYPE_XTY)

	# 第二字可識別的數字類型
	if begin < len(text) - 1:
		# 第一字是 [數字、元、兩]，而且有第二字可以判斷
		ch2 = text[begin+1]

		if u'元' == ch1:
			if u'年月'.find(ch2) >= 0:
				return (LCHR_FOUND, begin, TYPE_YM)
			else:
				# 第二個字確認不是中文數值
				return (LCHR_MISUNDERSTOOD, begin, 0)
		else:
			if u'兆億萬千百十'.find(ch2) >= 0:
				return (LCHR_FOUND, begin, TYPE_SPEAKING)
			else:
				return (LCHR_FOUND, begin, TYPE_DIGITS)
	else:
		# 第一字是 [數字、元、兩]，而且是全文的最後一字
		if u'零〇一二三四五六七八九'.find(ch1) >= 0:
			return (LCHR_FOUND, begin, TYPE_DIGITS)

	return (LCHR_NOTFOUND, 0, 0)

## 取純數值結尾
def end_of_digits_value(text, begin):
	imax = min(len(text), begin + 16)
	next = begin + 1
	while next < imax and u'零〇一二三四五六七八九'.find(text[next]) != -1:
		next = next + 1
	return next

## 取朗讀數值結尾
def end_of_speaking_value(text, begin):
	# 連接規則
	JUNCTION_RULES = {
		u'一二三四五六七八九兩': u'兆億萬千百十',
		u'兆億萬': u'零一二三四五六七八九兩',
		u'千': u'零一二三四五六七八九兆億萬兩',
		u'百十': u'零一二三四五六七八九兆億萬',
		u'零': u'一二三四五六七八九'
	}

	exp4 = 16
	exp1 = 4
	imax = min(len(text), begin + 31)
	next = begin + 1
	prev_chr = text[begin]
	while next < imax:
		next_chr = text[next]

		# 兆億萬指數遞減檢查
		if u'兆億萬'.find(next_chr) != -1:
			exp = EXP_OF_CHAR[next_chr]
			if exp < exp4:
				exp4 = exp
				exp1 = 4
			else:
				# 指數異常
				return next - 1

		# 千百十指數遞減檢查
		if u'千百十'.find(next_chr) != -1:
			exp = EXP_OF_CHAR[next_chr]
			if exp < exp1:
				exp1 = exp
			else:
				# 指數異常
				return next - 1

		# 連接規則檢查
		next_set = None
		for prev_set in JUNCTION_RULES:
			if prev_set.find(prev_chr) != -1:
				next_set = JUNCTION_RULES[prev_set]
				break

		# 正常結束
		if next_set is not None:
			if next_set.find(next_chr) == -1:
				return next

		prev_chr = next_chr
		next = next + 1

	# 如果執行到這裡，表示處理上有遺漏
	return False

## 取金融數值結尾
def end_of_finance_value(text, begin):
	# 連接規則
	JUNCTION_RULES = {
		u'壹貳參肆伍陸柒捌玖': u'兆億萬仟佰拾',
		u'兆億萬': u'零壹貳參肆伍陸柒捌玖',
		u'仟佰拾': u'零壹貳參肆伍陸柒捌玖兆億萬',
		u'零': u'壹貳參肆伍陸柒捌玖'
	}

	exp4 = 16
	exp1 = 4
	imax = min(len(text), begin + 31)
	next = begin + 1
	prev_chr = text[begin]
	while next < imax:
		next_chr = text[next]

		# 兆億萬指數遞減檢查
		if u'兆億萬'.find(next_chr) != -1:
			exp = EXP_OF_CHAR[next_chr]
			if exp < exp4:
				exp4 = exp
				exp1 = 4
			else:
				# 指數異常
				return next - 1

		# 千百十指數遞減檢查
		if u'仟佰拾'.find(next_chr) != -1:
			exp = EXP_OF_CHAR[next_chr]
			if exp < exp1:
				exp1 = exp
			else:
				# 指數異常
				return next - 1

		# 連接規則檢查
		next_set = None
		for prev_set in JUNCTION_RULES:
			if prev_set.find(prev_chr) != -1:
				next_set = JUNCTION_RULES[prev_set]
				break

		# 正常結束
		if next_set is not None:
			if next_set.find(next_chr) == -1:
				return next

		prev_chr = next_chr
		next = next + 1

	# 如果執行到這裡，表示處理上有遺漏
	return False

## 取 20-49 縮寫法數值結尾
def end_of_xty_value(text, begin):
	tlen = len(text)
	next = begin + 1
	if next < tlen and u'一二三四五六七八九'.find(text[next]) != -1:
		return next + 1
	else:
		return next

# 中文數字轉阿拉伯數字
def convert_digits_value(vstr):
	CDIGITS = u'〇一二三四五六七八九'
	ADIGITS = u'0123456789'

	# 零 => 〇
	vstr = vstr.replace(u'零', u'〇')

	# 轉換
	astr = u''
	for d in vstr:
		v = CDIGITS.find(d)
		astr = astr + ADIGITS[v]

	return astr

# 中文朗讀轉阿拉伯數字
def convert_speaking_value(vstr):
	CHAR_POS = {u'千': 0, u'百': 1, u'十': 2}
	CDIGITS  = u'零一二三四五六七八九'
	ADIGITS  = u'0123456789'

	vstr = vstr.replace(u'兩', u'二')

	d = u'1'
	tstr = [u'0', u'0', u'0', u'0']
	astr = u''
	exp4 = -1

	for c in vstr:
		if u'萬億兆'.find(c) != -1:
			# 兆 => 萬 的情況補零
			exp = EXP_OF_CHAR[c]
			if (exp4 - exp) == 8:
				astr = astr + u'0000'
			exp4 = exp

			# 轉換 4n 次方 (n>1)
			if d != u'':
				tstr[3] = d

			astr = astr + ''.join(tstr)
			tstr = [u'0', u'0', u'0', u'0']
			d = u''
		elif u'千百十'.find(c) != -1:
			# 轉換非 4n 次方
			pos = CHAR_POS[c]
			tstr[pos] = d
			d = u''
		else:
			# 轉換數字
			v = CDIGITS.find(c)
			d = ADIGITS[v]

	# 兆、億 => 個位數 的情況補零
	if exp4 > 4:
		astr = astr + u'0' * (exp4 - 4)
	
	# 合併 1~3 次方
	astr = astr + ''.join(tstr)
	astr = astr.lstrip(u'0')

	# 轉換最後一個數字
	if d != u'':
		# 最後一個數字可能不是個位數
		# * 兩萬二 22000 --- 3 次方、字串位置 -4
		# * 兩千二 2200 ---- 2 次方、字串位置 -3
		# * 兩百二 220 ----- 1 次方、字串位置 -2
		# * 兩萬零二 20002 - 0 次方、字串位置 -1
		# * 二 ------------ 0 次方、字串位置 -1

		if len(vstr) > 1 and u'百千萬億'.find(vstr[-2]) != -1:
			idx = -(EXP_OF_CHAR[vstr[-2]] - 1) - 1
			astr = astr[0:idx] + d + astr[idx+1:]
		else:
			astr = astr[0:-1] + d

	return astr

# 金融數值轉阿拉伯數字
def convert_finance_value(vstr):
	CHAR_MAP = {
		u'壹': u'一', u'貳': u'二', u'參': u'三',
		u'肆': u'四', u'伍': u'五', u'陸': u'六',
		u'柒': u'七', u'捌': u'八', u'玖': u'九',
		u'拾': u'十', u'佰': u'百', u'仟': u'千'
	}

	# 金融字元轉朗讀字元
	for (fc, sc) in CHAR_MAP.iteritems():
		vstr = vstr.replace(fc, sc)

	# 用朗讀法轉換
	return convert_speaking_value(vstr)

# 20~49 縮寫轉阿拉伯數字
def convert_xty_value(vstr):
	CDIGITS = u'..廿卅卌'
	ADIGITS = u'..234'

	v = CDIGITS.find(vstr[0])
	astr = ADIGITS[v]

	if len(vstr) == 1:
		astr = astr + u'0'
	else:
		astr = astr + convert_digits_value(vstr[1])

	return astr

## 內文日期轉 ISO 8601
def convert_iso_date(text):
	offset  = 0
	strout  = StringIO()
	pattern = re.compile(u'(\d{2,4})[年/](\d{1,2})[月/](\d{1,2})日?')

	m = pattern.search(text)
	while m is not None:
		yy = int(m.group(1))
		mm = int(m.group(2))
		dd = int(m.group(3))
		if yy < 1000:
			yy = yy + 1911
		
		strout.write(text[offset:m.start(0)])
		strout.write('%04d-%02d-%02d' % (yy, mm, dd))
		offset = m.end(0)
		m = pattern.search(text, offset)

	if offset < len(text):
		strout.write(text[offset:])

	ctext = strout.getvalue()
	strout.close()

	return ctext

## 阿拉伯數字轉中文數字
def convert_chinese_numerals(text):
	strout = StringIO()
	chdigits = u'零一二三四五六七八九'

	for c in text:
		if re.match('\d', c) is not None:
			d = int(c)
			strout.write(chdigits[d])
		else:
			strout.write(c)

	ctext  = strout.getvalue()
	strout.close()

	return ctext