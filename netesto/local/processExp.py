#!/usr/bin/python

import sys, random, os.path, commands, getopt

flog = None
desc = None
otherList = []

#--- isFloat
def isFloat(s):
    try: return (float(s),True)[1]
    except (ValueError, TypeError), e: return False

#--- putHtml
def putHtml(fout, fieldList, path, fname, link, title):
#  fout.write('Content-type: text/html\n\n')
    fout.write('<HTML> <HEAD> <TITLE>'+title+' </TITLE> </HEAD>'+'\n')
    fout.write('<BODY>\n')
#  fout.write(inputLine+'\n')
    fout.write('<FORM name="table" method="post" action="http://localhost/Exp/cgi-exec/exp.py" enctype="multipart/form-data">\n')
    fout.write('<input type=hidden name="File" value="'+path+'/'+fname+'">\n')
    fout.write('<input type=hidden name="Path" value="'+path+'">\n')
    fout.write('<input type=hidden name="relPath", value="'+relPath+'">\n')
    fout.write('<input type=hidden name="IterFile" value="'+link+'">\n')
    fout.write('</FORM>\n')
    fout.write('<script type="text/javascript">\ndocument.table.submit()\n</script>\n</BODY>\n</HTML>\n')

#----- putCsvHeader
def putCsvHeader(fout, fieldList):
    count = 0
    for f in fieldList:
        if count == 0:
            fout.write(f)
        else:
            fout.write(','+f)
        count += 1
    fout.write('\n')

#--- putCsvRow
def putCsvRow(fout, rowDict, fieldList):
    count = 0
    for f in fieldList:
        if f in rowDict:
            v = str(rowDict[f])
            v = v.strip()
            if v == 'None':
                v = ' '
        else:
            v = ' '
        if count == 0:
            fout.write(v)
        else:
            fout.write(','+v)
        count += 1
    fout.write('\n')

def getFloat(s):
    n = len(s)
    if s[n-1:] == 'M':
        val = float(s[:n-1]) * 1000000
    elif s[n-1:] == 'K':
        val = float(s[:n-1]) * 1000
    elif s[n-1:] == 'G':
        val = float(s[:n-1]) * 1000000000
    else:
        val = float(s)
    return val

def processRow(fieldList, fieldVal, fieldOpDict):
    global desc
    global otherList

    row = []
    print >>flog, 'Creating row'
    for f in fieldList:
        if f in fieldVal:
            print >>flog, '  doing '+f
            if fieldOpDict[f] == 'avg':
                if fieldVal[f][0] == None or fieldVal[f][1] == 0:
                    row.append(f+'=')
                else:
                    if f != 'retransPkts%':
                        v = "%.3f" % float(fieldVal[f][0]/fieldVal[f][1])
                    else:
                        v = "%.3f" % float(fieldVal[f][0]/fieldVal[f][1])
                    row.append(f+'='+str(v))
            elif fieldOpDict[f] == 'sumRateDur':
                if fieldVal[f][0] == None or fieldVal[f][1] == 0:
                    row.append(f+'=')
                else:
                    v = "%.3f" % float(fieldVal[f][0]/fieldVal[f][1])
                    row.append(f+'='+str(v))
            else:
                if f == 'desc' and fieldVal[f][0] == None and desc != None:
                    row.append(f+'='+desc)
                else:
                    breakFlag = False
                    for other in otherList:
                        if f == other[0]:
                            row.append(f+'='+other[1])
#                            print "other found: ", f+'='+other[1]
                            breakFlag = True
                            break
                    if breakFlag:
                        continue
                    if isFloat(fieldVal[f][0]) and f != 'exp' and \
                        f != 'retransPkts%':
                        s = "%.1f" % float(fieldVal[f][0])
                    else:
                        s = str(fieldVal[f][0])
                    if len(s) >= 1 and s[-1] == '/':
                        s = s[:-1]
                    row.append(f+'=' + s)
        else:
            print f, 'Not in fieldVal'
    print >>flog, 'Row:', row
    return row

# ------------------------------  Main  ------------------

action = 'create'
field_fn = 'fields.txt'
#foutName = '/home/brakmo/www/Experiments/nv/hw/1G-1G/1/exp.html'
foutName = '/Library/webServer/Documents/Exp/exp.html'
fname = 'exp'
#path = '/home/brakmo/www/Experiments/nv/hw/1G-1G'
path = '/Library/webServer/Documents/Exp'
relPath = '/Exp'
outPath = '.'
title = 'HW Exp'
rfile = ''
link = 'exp.html'

fieldList = []

opt_list = ['outPath=', 'relPath=', 'path=', 'fname=', 'link=', 'fields=', 'row=', 'title=', 'rfile=', 'desc=', 'other=' ]

try:
    opts, args = getopt.getopt(sys.argv[1:], 'ca', opt_list)
except getopt.GetoptError, err:
    print str(err)
    sys.exit(-1)

row = []
rowList = []

for opt in opts:
    key = opt[0]
    val = opt[1]
    if key == '-c':
        action = 'create'
    elif key == '-a':
        action = 'add'
    elif key == '--path':
        path = val
    elif key == '--relPath':
        relPath = val
    elif key == '--outPath':
        outPath = val
    elif key == '--fname':
        fname = val
    elif key == '--link':
        link = val
    elif key == '--debug':
         flog = open(val, 'a')
         flog.write('\nNEW FILE\n--------\n')
    elif key == '--fields':
        field_fn = val
    elif key == '--row':
        row = val.split(' ')
        rowList.append(row)
    elif key == '--title':
        title = val
    elif key == '--rfile':
        rfile = val
    elif key == '--desc':
        desc = val
    elif key == '--other':
#        print "--ohter="+val
        otherList = []
        if val != '':
            tmpList = val.split(',')
            for e in tmpList:
                epair = e.split('=')
                otherList.append(epair)
#        print "otherList:", otherList

if flog == None:
    flog = open('/dev/null', 'w')

print >>flog, 'opts = ', opts
print >>flog, 'args = ', args

#fname_use = open('processExp.use', 'r')
#for iline in fname_use:
#    line = iline.strip()
#    if len(line) == 0 or line[0] == '#':
#        continue
#    kv = line.split('=')
#    if len(kv) < 2:
#        continue
#    if kv[0] == 'fname':
#        fname = kv[1]
#fname_use.close()

fieldOpDict = {}
fin = open(field_fn, 'r')
for iline in fin:
    line = iline.strip()
    if len(line) == 0:
        continue
    if line[0] != '#':
        field = line.split(':')
        fieldList.append(field[0])
        fieldOpDict[field[0]] = field[1]
fin.close()

fieldVal = {}
lineNum = 0

if rfile != '':
    print >>flog, 'rfile:'+rfile
    for f in fieldList:
        fieldVal[f] = [None, 0]
    fin = open(rfile, 'r')
    dur = None
    maxDur = 0
    rate = None
    for iline in fin:
        line = iline.strip()
        if len(line) == 0 or line[0] == '#':
            continue
        print >>flog, 'LINE:' + line
        if line.find('---') >= 0:
            rowList.append(processRow(fieldList, fieldVal, fieldOpDict))
            for f in fieldList:
                fieldVal[f] = [None, 0]
            dur = None
            maxDur = 0
            rate = None
            lineNum += 1
            print >>flog, 'Line #:', lineNum
            continue
        keyval = line.split(':')
        if len(keyval) < 2:
            continue
        key = keyval[0]
        val = keyval[1]

        if key == 'dur':
            dur = getFloat(val)
            if dur > maxDur:
                maxDur = dur
            if rate != None and 'rate' in fieldOpDict and fieldOpDict['rate'] == 'sumRateDur':
                rate *= dur
                if fieldVal[key][0] == None:
                    fieldVal[key][0] = rate
                else:
                    fieldVal[key][0] += rate
                rate = None
                dur = None
                fieldVal[key][1] = maxDur
        elif key == 'rate':
          rate = getFloat(val)

        print >>flog, 'rfile - key:'+key+' val:'+val
        if not key in fieldList:
            print >>flog, 'rfile - key not in fieldList'
            continue
        if key in fieldOpDict:
            print >>flog, '          op:'+fieldOpDict[key]
            print >>flog, '           0:'+str(fieldVal[key][0])
            print >>flog, '           1:'+str(fieldVal[key][1])
            if fieldOpDict[key] != 'one' and val == '':
                continue
            if fieldOpDict[key] == 'sum':
                if fieldVal[key][0] == None:
                    fieldVal[key][0] = getFloat(val)
                else:
                    fieldVal[key][0] += getFloat(val)
            elif fieldOpDict[key] == 'sumRateDur':
                if dur != None:
                    newVal = getFloat(val)*dur
                    if fieldVal[key][0] == None:
                        fieldVal[key][0] = newVal
                    else:
                        fieldVal[key][0] += newVal
                    fieldVal[key][1] = maxDur
                    rate = None
                    dur = None
            elif fieldOpDict[key] == 'all':
                if fieldVal[key][0] == None:
                    fieldVal[key][0] = val + '/'
                elif fieldVal[key][0].find(val+'/') < 0:
                    fieldVal[key][0] += val + '/'
            elif fieldOpDict[key] == 'avg':
                if fieldVal[key][0] == None:
                    fieldVal[key][0] = getFloat(val)
                else:
                    fieldVal[key][0] += getFloat(val)
                fieldVal[key][1] += 1
            elif fieldOpDict[key] == 'max':
                if fieldVal[key][0] == None:
                    fieldVal[key][0] = getFloat(val)
                elif float(val) > fieldVal[key][0]:
                    fieldVal[key][0] = getFloat(val)
            elif fieldOpDict[key] == 'one':
                if fieldVal[key][0] == None:
                    fieldVal[key][0] = val
                elif val != fieldVal[key][0]:
                    #print >>flog, 'ERROR: non matching for '+key+': '+str(val)+', '+str(fieldVal[key][0])
                    if fieldVal[key][0].find('+...') < 0:
                        fieldVal[key][0] += '+...'
            elif fieldOpDict[key] == 'min':
                if fieldVal[key][0] == None:
                    fieldVal[key][0] = getFloat(val)
                elif float(val) < fieldVal[key][0]:
                    fieldVal[key][0] = getFloat(val)

fin.close()

print >>flog, 'Fields'
print >>flog, fieldList

if action == 'create':
    fout_html = open(outPath+'/'+fname+'.html', 'w')
    putHtml(fout_html, fieldList, path, fname, link, title)
    fout_csv = open(outPath+'/'+fname+'.csv', 'w')
    putCsvHeader(fout_csv, fieldList)

elif action == 'add':
    fout_html = open(outPath+'/'+fname+'.html', 'a')
    fout_csv = open(outPath+'/'+fname+'.csv', 'a')

    print >>flog, 'len(rowList):', len(rowList)
    for row in rowList:
        rowDict = {}
        if len(row) > 0:
            for r in row:
                elem = r.split('=')
                rowDict[elem[0]] = elem[1]
            print >>flog, 'Row'
            print >>flog, row
            putCsvRow(fout_csv, rowDict, fieldList)

fout_html.close()
fout_csv.flush()
os.fsync(fout_csv.fileno())
fout_csv.close()
flog.close()
