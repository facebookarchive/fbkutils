#!/usr/local/bin/python

import sys
import os
import psPlot

def processFile(inFilename):
    inFile = open(inFilename, 'r')
    reqSize = 0
    replySize = 0
    units = None
    X = []
    Y = []
    ca = "?"
    flow = "?"
    lastX = 0

    for line in inFile:
        line = line.strip()
#		print 'Line: ', line
        kv = line.split('=')
#		print '  kv: ', kv
        if units == None and kv[0].find('NETPERF_UNITS') >= 0:
            units = kv[1]
        elif kv[0].find('NETPERF_INTERVAL') >= 0:
            i = float(kv[1])
        elif kv[0].find('NETPERF_ENDING') >= 0:
            x = float(kv[1])
            if (x - i) > lastX:
                X.append(x - i)
            else:
                X.append(lastX + 0.01)
            X.append(x)
            lastX = x
        elif kv[0].find('NETPERF_INTERIM_RESULT') >= 0:
            y = float(kv[1])
            Y.append(y)
            Y.append(y)
        elif kv[0] == 'REQUEST_SIZE':
            reqSize = int(kv[1])
        elif kv[0] == 'RESPONSE_SIZE':
            replySize = int(kv[1])
        elif kv[0] == 'CA':
            ca = kv[1]
        elif kv[0] == 'FLOW':
            flow = kv[1]

    if units == 'Trans/s':
        i = 0
        if reqSize > replySize:
            size = reqSize
        else:
            size = replySize
        for y in Y:
            Y[i] = reqSize * 8 * y / 1000000
            i += 1

    return X, Y, ca, flow

def addGraphs(XList, YList, xmin=None, xmax=None):

    if len(XList) <= 1:
        return None, None

    # Find minimum and maximum of X lists
    if xmin == None or xmax == None:
        xmin = XList[0][0]
        xmax = XList[0][0]
        for X in XList:
            xmin = min(xmin, min(X))
            xmax = max(xmax, max(X))

    # Find average xinc
    xincSum = 0.0
    xincCount = 0
    for X in XList:
        i = 0
        for x in X:
            if i > 0:
                xincSum += X[i] - X[i-1]
                xincCount += 1
            i += 1
    if xincCount == 0:
        return None, None
    xinc = xincSum / xincCount
    if xinc == 0:
        return None, None
    x = xmin
    n = int((xmax - xmin)/xinc + 1)
    #print 'xmin:%.2f  xmax:%.2f  xinc:%.2f' % (xmin, xmax, xinc)

    listIndex = -1
    firstTime = True
    for X in XList:
        listIndex += 1
        Y = YList[listIndex]
        if firstTime:
            firstTime = False
            Xsum = X
            Ysum = Y
        else:
            newXsum = []
            newYsum = []
            index = 0
            sumIndex = 0
            xsum = Xsum[0]
            x = X[0]
            if x > xsum:
                sumIndex = 0
                ysum = Ysum[sumIndex]
                index = -1
                y = 0
            elif x < xsum:
                sumIndex = -1
                ysum = 0
                index = 0
                y = Y[index]
            else:
                sumIndex = 0
                index = 0
                ysum = Ysum[sumIndex]
                y = Y[index]
            while True:
                if x > xsum:
                    newXsum.append(xsum)
                    newYsum.append(ysum + y)
                    sumIndex += 1
                elif x < xsum:
                    newXsum.append(x)
                    newYsum.append(ysum + y)
                    index += 1
                else:
                    newXsum.append(x)
                    newYsum.append(ysum + y)
                    index += 1
                    sumIndex += 1
                if index < len(X):
                    if index >= 0:
                        x = X[index]
                        y = Y[index]
                else:
                    while sumIndex < len(Xsum):
                        xsum = Xsum[sumIndex]
                        ysum = Ysum[sumIndex]
                        newXsum.append(xsum)
                        newYsum.append(ysum)
                        sumIndex += 1
                    break
                if sumIndex < len(Xsum):
                    if sumIndex >= 0:
                        xsum = Xsum[sumIndex]
                        ysum = Ysum[sumIndex]
                else:
                    while index < len(X):
                        x = X[index]
                        y = Y[index]
                        newXsum.append(x)
                        newYsum.append(y)
                        index += 1
                    break
            Xsum = newXsum
            Ysum = newYsum

#            for xnew in X:
#                ynew = Y[sumIndex]
#                if xnew > xold:
#                    newXsum[newSumIndex] = x
#
#    Xsum = XList[0]
#    Ysum = YList[0]
#
#
#    # fill Xsum list
#    x = xmin
#    i = 0
#    while x < xmax and i < n:
#        x = xmin + i * xinc
#        Xsum[i] = x
#        i += 1
#
#    # fill YSum list
#    Ysum = [0.0]*n
#    listIndex = 0
#    for X in XList:
#        Y = YList[listIndex]
#        #print 'listIndex:', listIndex
#        listIndex += 1
#        i = 0
#        isum = 0
#        x0 = xmin - xinc
#        y0 = 0
#        x1 = X[i]
#        y1 = Y[i]
#        for x in Xsum:
#            while x > x1 and i < len(X) - 1:
#                x0 = x1
##                y0 = y1
#                i += 1
#                x1 = X[i]
#                y1 = Y[i]
##            if i >= len(X) - 1:
#            if i > len(X) - 1:
#                continue
#            if i == 0:
#                y = 0.0
#            else:
#                y = y0 + (y1 - y0)*(x - x0)/(x1 - x0)
##			print 'x:%.2f y:%.2f x0:%.2f x1:%.2f y0:%.2f y1:%.2f' \
##				% (x, y, x0, x1, y0, y1)
#            Ysum[isum] += y
#            if Ysum[isum] > 10*1024.0:
#                Ysum[isum] = 10*1024.0
#            isum += 1
    return Xsum, Ysum

#
# MAIN
#
if len(sys.argv) < 2:
    print "Usage: %s <input netperf files separated by spaces> " % sys.argv[0]
    sys.exit(1)

XList = []
YList = []
caList = []
flowList = []
flowNames = []

xmax = None
xmin = None

firstTime = True

for name in sys.argv[1:]:
    X, Y, ca , flow = processFile(name)
    if firstTime:
        if len(X) > 0 and len(Y) > 0:
            firstTime = False
            xmin = X[0]
            xmax = X[0]
            ymin = Y[0]
            ymax = Y[0]
    if len(X) == 0 or len(Y) == 0:
        continue
    XList.append(X)
    YList.append(Y)
    caList.append(ca)
    flowList.append(flow)
    flowNames.append(ca + ' ' + flow)
    if xmax != None:
        xmin = min(xmin, min(X))
        xmax = max(xmax, max(X))
        ymin = min(ymin, min(Y))
        ymax = max(ymax, max(Y))

# print 'xmin:%.2f, xmax:%.2f, ymin:%.2f, ymax:%.2f' % (xmin, xmax, ymin, ymax)

for X in XList:
    i = 0
    for x in X:
        X[i] = x - xmin
        i += 1
if xmax != None:
    xmax -= xmin
    xmin -= xmin
else:
    sys.exit(2)

#print "Callong addGraphs"
Xsum, Ysum = addGraphs(XList, YList, xmin, xmax)

if Xsum != None:
    L =  ['Sum']
    L.extend(flowNames)
    flowNames = L
    L = [Xsum]
    L.extend(XList)
    XList = L
    L = [Ysum]
    L.extend(YList)
    YList = L
    ymax = max(ymax, max(Ysum))
    firstGraphSum = True
    colOffset = 0
else:
    firstGraphSum = False
    colOffset = 1

path = os.path.dirname(sys.argv[1])

#print "Staring plots"
p = psPlot.PsPlot(path + '/' + 'rates', '', '', 1)
p.SetPlotBgLevel(0.95)
p.SetPlot(xmin, xmax, 0, 0, ymax, 0, 'Time in seconds', 'Goodput Mbps',
    'Goodputs')
p.seriesTitle = 'Flows'
p.SeriesNames(flowNames)

i = 0
for X in XList:
    Y = YList[i]
    if len(X) < 2:
        continue
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
        X.append(X[-1] + inc)
        X.append(xmax)
        Y.append(0.0)
        Y.append(0.0)
    if firstGraphSum == True:
        p.PlotData(1, X, Y,
#			'', '', '2.0 ' + p.SetColor(p.colors[i % p.colorsN]) +
#			' plotStraightLinesC')
            '', '', '3 2.0 ' + p.SetColor(p.colors[i % p.colorsN]) +
            ' plotNAvgStraightLinesC')
        firstGraphSum = False
    else:
        p.PlotData(1, X, Y,
            '', '', '0.4 ' + p.SetColor(p.colors[(i + colOffset) % p.colorsN])
            + ' plotStraightLinesC')
    i += 1

image = p.GetImage()
#print 'Plot: ', image
