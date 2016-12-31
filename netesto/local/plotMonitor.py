#!/usr/local/bin/python

# plotMonitor.py - Tool to graph values from ss or inet_monitor
#
# Copyright (C) 2016, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the LICENSE
# file in the root directory of this source tree.

import sys
import os
import psPlot

def processFileRetrans(inFilename, field):
    inFile = open(inFilename, 'r')
    X = []
    delay = 0.0
    firstTime = True
    lastY = -340987
    for line in inFile:
        line = line.strip()
        kvals = line.split(' ')
        for kv in kvals:
            if kv.find(':') < 0:
                continue
            key, val = kv.split(':')
            if firstTime:
                firstTime = False
                if key == 'delay':
                    delay = float(val)
            if key == 'time':
                x = float(val) + delay
            elif key == field:
                y = float(val)
                if y > lastY:
                    X.append(x)
#					Y.append(y)
                lastY = y
    inFile.close()
    return X

def processFile(inFilename, field):
    inFile = open(inFilename, 'r')
    X = []
    Y = []
    ca = "?"
    delay = 0.0
    firstTime = True
    if inFilename.find('ss') >= 0:
        ssFlag = True
        time = 0.0
        firstTime = False
    else:
        ssFlag = False

    for line in inFile:
        line = line.strip()
#		print 'Line: ', line
        kvals = line.split(' ')

        for kv in kvals:
            if ssFlag and kv.find(field) < 0:
                continue
            if kv.find(':') < 0:
                continue
            key, val = kv.split(':')
            if key == field:
                if ssFlag:
                    val = val.split('/')[0]
                if field == 'send':
                    p = val.find('bps')
                    if p > 0:
                        m = val[p-1]
                        val = float(val[:p-1])
                        if m == 'K':
                            val /= 1000.0
                        elif m == 'G':
                            val *= 1000.0
                Y.append(float(val))
                if ssFlag:
                    X.append(time + delay)
                    time += 0.200
            elif key == 'time':
                X.append(float(val) + delay)
            if firstTime:
                if key == 'ca':
                    ca = val
                    firstTime = False
                elif key == 'delay':
                    delay = float(val)
                    if delay > 0:
                        X.append(0.0)
                        X.append(delay)
                        Y.append(0.0)
                        Y.append(0.0)
    inFile.close()
    return X, Y, ca


if len(sys.argv) < 3:
    #print "Usage: %s <field> <input files separated by spaces> " % sys.argv[0]
    sys.exit(1)

field = sys.argv[1]
#print 'Field:', field

XList = []
YList = []
caList = []
flowList = []
flowNames = [None]
Xdrop = []

firstTime = True

for name in sys.argv[2:]:
    flow = os.path.basename(name)
    flow = flow.replace('monitor.', '')
    flow = flow.replace('.out', '')
    #print 'processing:', name, ' flow:', flow
    X, Y, ca = processFile(name, field)
    if name.find('ss') < 0:
        Xd = processFileRetrans(name, 'retrans_total')
        if len(Xd) > 0:
            Xdrop.extend(Xd)
    if len(X) != len(Y) or len(X) == 0:
        continue

    if firstTime:
        firstTime = False
        xmin = X[0]
        xmax = X[0]
        ymin = Y[0]
        ymax = Y[0]

    XList.append(X)
    YList.append(Y)
    caList.append(ca)
    flowList.append(flow)
    flowNames.append(ca + ' ' + flow)
    xmin = min(xmin, min(X))
    xmax = max(xmax, max(X))
    ymin = min(ymin, min(Y))
    ymax = max(ymax, max(Y))

if len(XList) == 0:
    sys.exit(0)

#print 'xmin:%.2f, xmax:%.2f, ymin:%.2f, ymax:%.2f' % (xmin, xmax, ymin, ymax)

for X in XList:
    i = 0
    for x in X:
        X[i] = x - xmin
        i += 1

path = os.path.dirname(sys.argv[2])

p = psPlot.PsPlot(path + '/' + field, '', '', 1)
p.SetPlotBgLevel(0.95)
if field == 'rtt':
    yTitle = 'RTT (ms)'
else:
    yTitle = field

p.SetPlot(0, xmax-xmin, 0, 0, ymax, 0, 'Time in seconds', yTitle,
    field)
p.seriesTitle = 'Flows'
p.SeriesNames(flowNames)

#p.PlotVBars(Xdrop, '{ 0.7 0.6 0.6 setrgbcolor } plotVBarsC')
p.PlotVBars(Xdrop, '{ 0.9 0.8 0.8 setrgbcolor } plotVBarsC')

i = 0
for X in XList:
    Y = YList[i]
    inc = X[1] - X[0]
    if X[0] > 0:
        Xt = []
        Yt = []
        Xt.append(0.0)
        Xt.append(X[0] - inc)
        Xt.extend(X)
        X = Xt
        Yt.append(0.0)
        Yt.append(0.0)
        Yt.extend(Y)
        Y = Yt
    if X[-1] < xmax:
        X.append(X[-1] + 0.1)
        X.append(xmax)
        Y.append(0.0)
        Y.append(0.0)
    p.PlotData(1, X, Y,
        '', '', '0.4 ' + p.SetColor(p.colors[(i + 1) % p.colorsN]) +
        ' plotStraightLinesC')
    i += 1

image = p.GetImage()
#print 'Plot: ', image

