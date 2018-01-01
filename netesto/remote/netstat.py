#!/usr/local/bin/python

import sys

def processNames(namesStr):
    namePosDict = {}
    nameList = []
    pos = 0
    names = namesStr.split()
    for name in names:
        if name.find('xxxx') >= 0:
            continue
        nameList.append(name)
        namePosDict[name] = pos
        pos += 1
    return namePosDict, nameList

def processVals(nameList, valuesStr):
    valuesDict = {}
    valuesList = valuesStr.split()
    pos = 0
    for value in valuesList:
        if value.find('xxxx') >= 0:
            continue
        valuesDict[nameList[pos]] = value
        pos += 1
    return valuesDict

def processOne(namesStr, fieldsDict, valuesStr):
    namePosDict, nameList = processNames(namesStr)
    nameValDict = processVals(nameList, valuesStr)

    for name in nameList:
        if len(fieldsDict) > 0 and not name in fieldsDict:
            continue
        value = nameValDict[name]
        if name.find(':') > 0:
            print "\n*** ", name
            continue
        print '%25s  %s' % (name, value)


def processDiff(namesStr, fieldsDict, valuesBeforeStr, valuesAfterStr):
    namePosDict, nameList = processNames(namesStr)
    nameValBeforeDict = processVals(nameList, valuesBeforeStr)
    nameValAfterDict = processVals(nameList, valuesAfterStr)

    for name in nameList:
        if len(fieldsDict) > 0 and not name in fieldsDict:
            continue
        valueBefore = nameValBeforeDict[name]
        valueAfter = nameValAfterDict[name]
        if name.find(':') > 0:
            print "\n*** ", name
            continue
        valueDiff = int(valueAfter) - int(valueBefore)
        if valueDiff != 0:
            print '%25s  %6d' % (name, (valueDiff))
        else:
            print '%d' % (valueDiff)

def usage():
    print ""
    print "Usage: netstat.py [-f <fields>] <netstat-file>"
    print "       pretty print netstat output"
    print ""
    print "       netstat.py [-f <fields> <netstat-file0> <netstat-file1>"
    print "       pretty print non-zero difference between netstat files"
    print ""
    print "  args:"
    print "       -f       only print fields in list <fields>"
    print "                Example: netstat -f 'TCPHPHits,TCPFullUndo' /proc/net/netstat"
    sys.exit(0)

print ""
argc = len(sys.argv)

i = 1
inFiles = []
fieldsDict = {}
while i < argc:
    a = sys.argv[i]
    if a == '-h' or a == '--help':
        usage()
    elif a == '-f':
        i += 1
        if i >= argc:
            print "ERROR: field list missing"
            usage()
        fieldsStr = sys.argv[i]
        fields = fieldsStr.split(',')
        for f in fields:
            fieldsDict[f] = 1
    else:
        inFiles.append(sys.argv[i])
    i += 1

if len(inFiles) == 1:
    fin = open(inFiles[0], "r")
    nameFlag = True
    for line in fin:
        if nameFlag:
            nameStr = line
        else:
            valStr = line
            processOne(nameStr, fieldsDict, valStr)
        nameFlag = not nameFlag
else:
    fin1 = open(inFiles[0], "r")
    fin2 = open(inFiles[1], "r")
    nameFlag = True
    nameStrList = []
    valStrList1 = []
    valStrList2 = []
    for line in fin1:
        if nameFlag:
            nameStrList.append(line)
        else:
            valStrList1.append(line)
        nameFlag = not nameFlag
    nameFlag = True
    for line in fin2:
        if not nameFlag:
            valStrList2.append(line)
        nameFlag = not nameFlag
    i = 0
    for nameStr in nameStrList:
        processDiff(nameStr, fieldsDict, valStrList1[i], valStrList2[i])
        i += 1

print ""
