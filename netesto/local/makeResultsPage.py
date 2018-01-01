#!/usr/local/bin/python

import sys
import os

htmlHeader = [
    '<HTML>',
    '<HEAD>',
    '  <TITLE>Exp</TITLE>',
    '  <style>',
    '  body {font-family: verdana}',
    '  table { border: 1px solid black; }',
    '  th, td { padding-left: 15px; padding-right: 15px; }',
    '  table#t01 tr:nth-child(even) {',
    '    background-color: #eee;',
    '  }',
    '  table#t01 tr:nth-child(odd) {',
    '    background-color: #fff;',
    '  }',
    '  table#t01 th {',
    '    color: white;',
    '    background-color: black;',
    '  }',
    '</style>',
    '</HEAD>',
    '<BODY>'
]

fieldList = [
    'group', 'Test', 'host', 'server', 'instances', 'dur', 'delay',
    'Ca', 'min/avg/max Rates',
    'min/mean/max Latencies', 'p50/p90/p99 Latencies',
    'rtt', 'pingRtt', 'cwnd',
    'localRetrans', 'remoteRetrans', 'lost', 'retrans', 'retrans_total',
    'localCpu', 'remoteCpu',
    'client-tx-packets', 'client-tx-bytes', 'client-tx-packet-len',
    'client-rx-packets', 'client-rx-bytes', 'client-rx-packet-len',
    'tso', 'gso', 'lro', 'gro', 'rx-frames', 'tx-frames', 'adaptive-rx'
]

machinePath = None
nvFlag = False

def processFile(f):
    global machinePath
    global nvFlag

    #print 'processing:', f
    fieldDict = {}
    fin = open(f, 'r')
    for line in fin:
        line = line.strip()
        kv = line.split(':')
        if len(kv) < 2:
            continue
        key, val = kv
        fieldDict[key] = val
        if key == 'ca' and val == 'nv':
            nvFlag = True
        if key == 'host' or key == 'server':
            i = val.find('.')
            if i >= 0:
                mp = val[i:]
                if machinePath == None:
                    machinePath = mp
                elif machinePath != mp:
                    machinePath = ''
    fin.close()
    #print '  len:', len(fieldDict)
    return fieldDict

def processFields(fieldDict):
    if 'test' in fieldDict:
        test = fieldDict['test']
        if 'req' in fieldDict and 'reply' in fieldDict:
            test += ' ' + fieldDict['req'] + '/' + fieldDict['reply']
        fieldDict['Test'] = test
    if 'ca' in fieldDict:
        ca = fieldDict['ca']
        if 'nvPad' in fieldDict:
            ca += '/' + fieldDict['nvPad']
        fieldDict['Ca'] = ca
    if 'rate' in fieldDict:
        rates = fieldDict['rate']
        if 'rateMin' in fieldDict and 'rateMax' in fieldDict:
            rates = fieldDict['rateMin'] + '/' + rates + '/' + \
                fieldDict['rateMax']
        else:
            rates = '?/' + rates + '/?'
        fieldDict['min/avg/max Rates'] = rates
    if 'meanLatency' in fieldDict:
        lats = fieldDict['meanLatency']
        if 'minLatency' in fieldDict and 'maxLatency' in fieldDict:
            lats = fieldDict['minLatency'] + '/' + lats + '/' + \
                fieldDict['maxLatency']
        else:
            lats = '?/' + lats + '/?'
        fieldDict['min/mean/max Latencies'] = lats
    if 'p50Latency' in fieldDict:
        plats = fieldDict['p50Latency']
        if 'p90Latency' in fieldDict and 'p99Latency' in fieldDict:
            plats = plats + '/' + fieldDict['p90Latency'] + '/' + \
                fieldDict['p99Latency']
        else:
            plats = plats + '/?/?'
        fieldDict['p50/p90/p99 Latencies'] = plats
    return fieldDict


def writeHtmlHeader(exp):
    fout = open(exp + '/' + 'exp.html', 'w')
    for line in htmlHeader:
        fout.write('%s\n' % line)
    return fout

exp = sys.argv[1]
files = os.listdir(exp)
fieldDictList = []

for f in files:
    if f.find('.exp.out') >= 0 and f.find('all') < 0:
        fieldDict = processFile(exp + '/' + f)
        if len(fieldDict) > 0:
            fieldDict = processFields(fieldDict)
            fieldDictList.append(fieldDict)

if len(fieldDictList) == 0:
    #print 'len(fieldDictList) == 0!!'
    sys.exit(0)

fout = writeHtmlHeader(exp)
nextExp = str(int(exp) + 1)
prevExp = str(int(exp) - 1)
fout.write(('  <h2>Exp:%s %s &nbsp &nbsp &nbsp &nbsp ' +
    '<a href="../%s/exp.html">Prev</a> &nbsp &nbsp &nbsp ' +
    '<a href="../exp.html">Up</a> &nbsp &nbsp &nbsp ' +
    '<a href="../%s/exp.html">Next</a> </h2>\n') %
    (exp, fieldDictList[0]['expName'], prevExp, nextExp))
fout.write('  <table id="t01">\n')

if machinePath != '' and machinePath != None:
    for fd in fieldDictList:
        if 'client' in fd:
            v = fd['client']
            i = v.find('.')
            fd['client'] = v[:i]
        if 'server' in fd:
            v = fd['server']
            i = v.find('.')
            fd['server'] = v[:i]

for field in fieldList:
    if field == 'group':
        tx = 'th'
    else:
        tx = 'td'
    fout.write('    <tr>\n      <%s><b>%s</b></%s>\n' % (tx, field, tx))
    for fd in fieldDictList:
        if field in fd:
            v = fd[field]
        else:
            v = ' '
        fout.write('      <%s>%s</%s>\n' % (tx, v, tx))
    fout.write('    </tr>\n')

fout.write('  </table>\n')
fout.write('  <img src="rates.jpg">\n')
fout.write('  <img src="acked_rate.jpg">\n')
#fout.write('  <img src="send.jpg">\n')
fout.write('  <img src="cwnd.jpg">\n')
fout.write('  <img src="unacked.jpg">\n')
fout.write('  <img src="rtt.jpg">\n')
fout.write('  <img src="minrtt.jpg">\n')
fout.write('  <img src="retrans.jpg">\n')
fout.write('</BODY>\n</HTML>\n')
fout.close()

expName = fieldDictList[0]['expName']

fout = open('ExpList.html', 'a')
fout.write('<p><a href="%s/exp.html"> %s %s</a></p>\n' % (exp, exp, expName))
fout.close()
