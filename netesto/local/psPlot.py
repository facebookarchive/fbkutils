#!/usr/bin/python

import sys
import random
import os.path
import shutil
import commands
import types
import math

# gsPath = '/usr/local/bin/gs'
gsPath = 'gs'

#--- class PsPlot(fname, pageHeader, pageSubHeader, plotsPerPage)
#
class PsPlot(object):
    def __init__(self, fname, pageHeader, pageSubHeader, plotsPerPage):
        self.foutPath = os.path.dirname(fname)+'/'
        if self.foutPath == '/':
            self.foutPath = ''
        self.foutName = os.path.basename(fname)
        self.fname = fname+'.ps'
        self.pageHeader = pageHeader
        self.pageSubHeader = pageSubHeader
        self.plotsPerPage = plotsPerPage
        self.yfix1 = ''
        self.yfix2 = ''
        self.xGrid = 1
        self.yGrid = 1
        self.xUniform = False
        self.xLen = 6.5 #inches
        self.seriesTitle = ' '
        self.x0 = 0
        self.xInc = 0
        self.xCount = 0
        self.xList = []
        self.xDict = {}
        self.y1Inc = 0
        self.y1Count = 0
        self.y1LogScale = 0
        self.y2Inc = 0
        self.y2Count = 0
        self.y2LogScale = 0
        self.xOffset = 0
        self.colors = [ (0.7,0.7,0.7), (0,0,0.8), (0.8,0,0),
                        (0.42,0.55,0.14), (0.6,0.5,0.3), (0.6,0.2,0.8),
                        (0,0.8,0),
                        (0.4,0.3,0.5), (0.5,0.5,0.5), (0.8,0.0,0.0), (0,0,0) ]
        self.colorsN = 11
        self.colorRed = (0.8,0,0)
        self.colorGreen = (0,0.8,0)
        self.colorBlue = (0,0,0.8)
        self.colorAqua = (0,0.5,0.5)
        self.colorWhite = (1,1,1)
        self.ColorBlack = (0,0,0)

        self.xSize = 1800
        self.ySize = 900

        shutil.copy('plot-header.ps', self.fname)
        self.fout = open(self.fname, 'a')
        self.flog = open('/dev/null', 'a')
#    self.flog = open('./psPlot.out', 'a')
        if plotsPerPage == 4:
            print >>self.fout, '/doGraph { graph4v } def'
            print >>self.fout, '/nextGraph { nextGraph4v } def'
        elif plotsPerPage == 3:
            print >>self.fout, '/doGraph { graph3v } def'
            print >>self.fout, '/nextGraph { nextGraph3v } def'
        elif plotsPerPage == 2:
            print >>self.fout, '/doGraph { graph2v } def'
            print >>self.fout, '/nextGraph { nextGraph2v } def'
        else:
            print >>self.fout, '/doGraph { graph1v } def'
            print >>self.fout, '/nextGraph { nextGraph1v } def'
        print >>self.fout, '/showpage {\n 40 742 moveto'
        print >>self.fout, '/Helvetica findfont 12 scalefont setfont'
        if self.pageHeader != '':
            print >>self.fout, '(',self.pageHeader,') show'
        if self.pageSubHeader != '':
            print >>self.fout, '40 726 moveto\n (',self.pageSubHeader,') show'
        print >>self.fout, 'showpage\n} bind def'
        print >>self.fout, 'doGraph'

#--- End()
#
    def End(self):
        print >>self.fout, '\nshowpage\nend'
        self.fout.close()

#--- GetInc(vMin, vMax)
    def GetInc(self,vMin, vMax):
        ff = 1.0
        while vMax <= 1 and vMax > 0:
            ff *= 0.10
            vMin *= 10
            vMax *= 10
        v0 = int(vMin)
        v1 = int(vMax+0.99)
        f = 1
        w = v1 - v0
        if w == 0:
            v1 = v0 + 1
            w = 1
        while w/f >= 100:
            f *= 10
#    w = int(w/f)
        v0 = int(v0/f)
        v1 = int(v1/f)
        if (vMin % f) != 0  and  vMax == v1:
            v1 += 1
        w = v1 - v0

        if w <= 10:
            vInc = 1
        elif w <= 20:
            vInc = 2
        else:
            m = 10
            while w/m > 100:
                m *= 10
            if (v0 >= 0) and (v0 % m) != 0:
                v0 = int(v0 / m) * m
            if (v1 % m) != 0:
                v1 = int(v1 / m) * m + m
                w = v1 - v0
                if w <= 5*m:
                    vInc = m/2
                else:
                    vInc = m
            else:
                vInc = m

#    if (vMax/f)%vInc != 0  or  v1 % vInc != 0:
        if v1 % vInc != 0:
            v1 = int(v1/vInc)*vInc + vInc
        if (v0 % vInc) != 0:
            v0 = int(v0/vInc)*vInc
        v0 += vInc
        v0 *= (f*ff)
        v1 *= (f*ff)
        vInc *= (f*ff)
        return v0, v1, vInc

#--- ValueConvert(v)
#
    def ValueConvert(self, v, inc):
        if inc > 0:
            logInc = int(math.log10(v/inc))
            d = math.pow(10,logInc)
            if d == 0:
                d = 10.0
        else:
            d = 10.0
        if d == 1 and float(v)/inc > 1.0:
            d = 10.0

        if v >= 1000000000 and inc > 1:
            s = int(v/(1000000000/d))/d
            if s*d == int(s)*d:
                s = int(s)
            r = str(s) + 'G'

        elif v >= 1000000 and inc > 1:
            s = int(v/(1000000/d))/d
            if s*d == int(s)*d:
                s = int(s)
            r = str(s) + 'M'
        elif v >= 1000 and inc > 1:
            s = int(v/(1000/d))/d
            if s*d == int(s)*d:
                s = int(s)
            r = str(s) + 'K'
        elif v >= 1:
            s = int(v*d)/d
            if s*d == int(s)*d:
                s = int(s)
            r = str(s)
        else:
            r = str(int(v*100)/100.0)
        return r

#--- GetAxis(vBeg, vEnd, vInc, logFlag)
#
    def GetAxis(self, vBeg, vEnd, vInc, logFlag):
        fix = '{ 0 add }'
        if isinstance(vBeg,list):
            vList = vBeg
            vList.append(' ')
            self.xUniform = True
            v0 = 1
            v1 = len(vList)
            vi = 1
            fix = '{ '+str(v0-vi)+' sub '+str(vi)+' div }'
            logFlag = 0
        else:
            if vInc == 0:
                v0,v1,vi = self.GetInc(vBeg,vEnd)
            else:
                v0 = vBeg
                v1 = vEnd
                vi = vInc
            if vBeg > 0 and (logFlag==1 or (logFlag==0 and (vEnd/vBeg > 100))):
                v0 = vBeg
                v1 = vEnd
                logFlag = 1
                v0Log = math.log10(v0)
                t = math.ceil(v0Log)
                ff = math.modf(v0Log)
                if math.fabs(ff[0]) < math.fabs(v0Log)/1000 and t < 0:
                    t += 1
                logOffset = 0
                while t < 1:
                    logOffset += 1
                    t += 1
                v0 = math.pow(10,math.floor(v0Log)+1)
                v1 = math.pow(10,math.ceil(math.log10(v1)))
                vi = 1
                vList = []
                v = v0
                while v <= v1:
                    vList.append(self.ValueConvert(v,0))
                    v *= 10
                if v0 > 1:
                    logOffset -= (math.log10(v0) - 1)
#             substract 1 from above inside parent?
                fix = '{ dup 0 eq { } { log '+str(logOffset)+' add } ifelse }'
            else:
                logFlag = 0
                v = v0
                vList = []
                n = 0
                while True:
                    vList.append(self.ValueConvert(v,vi))
                    if v > vEnd:
 	                    break
                    n += 1
                    v = v0 + n*vi
                    fix = '{ '+str(v0-vi)+' sub '+str(vi)+' div }'
        print >>self.flog, 'v0:',v0,' vi:',vi,' v1:',v1,' (',vEnd,')'
        print >>self.flog, 'vList: ', vList
        print >>self.flog, 'logFlag: ', logFlag, ' fix: ', fix
        return v0,v1,vi,vList,fix,logFlag

#--- SetXLen(xlen)
    def SetXLen(self, xlen):
        self.xLen = xlen
        print >>self.fout, '/xAxisLen %.2f def' % self.xLen
        print >>self.fout, 'doGraph'
        return

#--- SetXSize(xsize)
    def SetXSize(self, xsize):
        self.xSize = xsize
        return

#--- SetYSize(ysize)
    def SetYSize(self, ysize):
        self.ySize = ysize
        return

#--- SetPlotBgLevel(level)
#
    def SetPlotBgLevel(self,level):
        print >>self.fout, '/plotBgLevel ', level, 'def\n'
        return

#--- SetPlotPercentDir(value)
    def SetPlotPercentDir(self,value):
        if value == 'Vertical':
            print >>self.fout, '/plotNumPercentDir 1 def\n'
        else:
            print >>self.fout, '/plotNumPercentDir 0 def\n'
        return

#--- SetPlotYLogScale(axis,value)
#
    def SetPlotYLogScale(self,axis,value):
        if value == 'Off':
            v = -1
        elif value == 'On':
            v = 1
        else:
            v = 0;
        if axis == 1:
            self.y1LogScale = v
        else:
            self.y2LogScale = v
        return

#--- SetPlot(xbeg,xend,xinc,ybeg,yend,yinc,xtitle,ytitle,title)
#
    def SetPlot(self,xbeg,xend,xinc,ybeg,yend,yinc,xtitle,ytitle,title):
        print >>self.fout, '\n\nnextGraph\n1 setlinewidth\n'
        (x0,x1,xi,xList,fix,logFlag) = self.GetAxis(xbeg,xend,xinc,0)
        self.x0 = x0
        self.xInc = xi
        self.xCount = len(xList)
        self.xList = xList
        self.xDict = {}
        k = 1
        for x in xList:
            self.xDict[x] = k
            k=k+1
        print >>self.fout, '/xfix ', fix, ' def\n'

        (y0,y1,yi,yList,fix,logFlag) = self.GetAxis(ybeg,yend,yinc,
             self.y1LogScale)
        self.y1Inc = yi
        self.y1Count = len(yList)
        self.yfix1 = '/yfix '+fix+' def\n /yinc yinc1 def'
        print >>self.fout, self.yfix1

        print >>self.fout, '[ '
        for x in xList:
            self.fout.write('('+str(x)+') ')
        self.fout.write(' ]\n[ ')
        for y in yList:
            self.fout.write('('+str(y)+') ')
        print >>self.fout, ' ]'
        print >>self.fout, '('+xtitle+')\n('+ytitle+')\naxes\n'
        print >>self.fout, self.xGrid, self.yGrid, ' grid\n'
        print >>self.fout, '/ymtitle ypos ylen add 10 add def\n'

# Multiple lines in title are separated by '|'
        print >>self.flog, 'Main Title: '+title
        titleLines = title.split('|')
        for t in titleLines:
            if len(t) > 0:
                print >>self.flog, '    '+t
                print >>self.fout, '('+t+')\n'
        print >>self.fout, 'Mtitles\n'
#    print >>self.fout, '('+title+')\nMtitles\n'

        if logFlag == 1:
            print >>self.fout, 'beginFunction\n'
            for ys in yList:
                factor = 1
                if ys[-1:] == 'K':
                    yss = ys[:-1]
                    factor = 1000
                elif ys[-1:] == 'M':
                    yss = ys[:-1]
                    factor = 1000000
                else:
                    yss = ys
                y = float(yss)*factor/10.0
                k = 2
                while k < 10:
                    print >>self.fout, 0, k*y
                    k += 1
            print >>self.fout, 'endFunction\n'
            print >>self.fout, '19  { 0 0 0 setrgbcolor }  plotSymbolsC\n'
        return y1

#--- SetPlot2(xbeg,xend,xinc,ybeg,yend,yinc,zbeg,zend,zinc,
#             xtitle,ytitle,ztitle,title)
#
    def SetPlot2(self,xbeg,xend,xinc,ybeg,yend,yinc,zbeg,zend,zinc,
                 xtitle,ytitle,ztitle,title):
        rv = self.SetPlot(xbeg,xend,xinc,ybeg,yend,yinc,xtitle,ytitle,title)
        (z0,z1,zi,zList,fix,logFlag) = self.GetAxis(zbeg,zend,zinc,self.y2LogScale)
        self.y2Inc = zi
        self.y2Count = len(zList)

        print >>self.fout, '/Flag2Yaxes 1 def'

        self.yfix2 = '/yfix '+fix+' def\n/yinc yinc2 def'
        print >>self.fout, 'axpos axlen add aypos aylen'

        self.fout.write('[ ')
        for z in zList:
            self.fout.write('('+str(z)+') ')
        self.fout.write(' ]')
        if ztitle != '':
            print >>self.fout, '('+ztitle+') vaxis2'
        if logFlag == 1:
            print >>self.fout, self.yfix2
            print >>self.fout, 'beginFunction\n'
            for zs in zList:
                factor = 1
                if zs[-1:] == 'K':
                    zss = zs[:-1]
                    factor = 1000
                elif zs[-1:] == 'M':
                    zss = zs[:-1]
                    factor = 1000000
                else:
                    zss = zs
                y = float(zss)*factor/10.0
                k = 2
                while k < 10:
                    print >>self.fout, self.xCount, k*y
                    k += 1
            print >>self.fout, 'endFunction\n'
            print >>self.fout, '18  { 0.72 0.52 0.5 setrgbcolor }  plotSymbolsC\n'
        return rv

#--- SetColor(color)
#
    def SetColor(self, color):
        rv = ' { '+str(color[0])+' '+str(color[1])+' '+str(color[2])+ \
             ' setrgbcolor } '
        return rv

#--- GetColorIndx(indx)
#
    def GetColorIndx(self, indx):
        color = self.colors[indx % self.colorsN]
        rv = ' { '+str(color[0])+' '+str(color[1])+' '+str(color[2])+ \
             ' setrgbcolor } '
        return rv

#--- SetColorIndx(indx, r, g, b)
#
    def SetColorIndx(self, indx, r, g, b):
        self.colors[indx][0] = r
        self.colors[indx][1] = g
        self.colors[indx][2] = b
        return rv

#--- outputPS(string)
#
    def outputPS(self, s):
        print >>self.fout, s

#--- SeriesNames(names)
#
    def SeriesNames(self, names):
        indx = len(names) - 1
        if indx == 0:
            return

        print >>self.fout, '('+self.seriesTitle+')'
        while indx >= 0:
            if names[indx] != None:
                 print >>self.fout, '('+names[indx]+') '
                 print >>self.fout, self.SetColor(self.colors[indx % self.colorsN])
            indx -= 1
        print >>self.fout, 'fdescriptionsC'

#--- PlotVBars(xList, type)
#
    def PlotVBars(self, xList, type):
        flog = self.flog
        print >>self.fout, self.yfix1
        print >>self.fout, 'beginFunction\n'
        endFun = 'endFunction\n'
        indx = 0
        for x in xList:
            if x == ' ' and indx == len(xList)-1:
                continue
            indx += 1
            print >>self.fout, x
            if (indx != 0) and (indx % 1000) == 0:
                print >>self.fout, endFun+type+'\nbeginFunction\n'
                print >>self.fout, x
        print >>self.fout, endFun, type, '\n'
        return

#--- PlotData(axis, xList, yList, zList, id, type)
#
    def PlotData(self, axis, xList, yList, zList, id, type):
        flog = self.flog
        print >>flog, 'graph xList: ', self.xList, ' xList: ', xList, \
                      ' yList: ', yList
        print >>self.fout, '%\n% Plot '+id+'\n%\n'
        print >>self.fout, '/xfix { ', self.x0 - self.xInc - self.xOffset,' sub ', self.xInc, ' div ', 0,' add } def\n'
        if axis == 2:
            print >>self.fout, self.yfix2
        elif axis == 1:
            print >>self.fout, self.yfix1
#    else:
#      print >>self.fout, '/yfix { 0 add } def\n'
        print >>self.fout, 'beginFunction\n'
        if isinstance(zList,list):
            endFun = 'endFunctionW\n'
        else:
            endFun = 'endFunction\n'

        indx = 0
        for x in xList:
            if x == ' '  and  indx == len(xList)-1:
                continue
            if len(yList) <= indx:
                continue
            y = yList[indx]
            if isinstance(zList,list):
                if len(zList) <= indx:
                    continue
                z = zList[indx]
            else:
                z = ''
            indx += 1
            if self.xUniform == True:
                g_indx = self.xDict[x]
                print >>self.fout, g_indx, y, z
            else:
                print >>self.fout, x, y, z
            if (indx != 0) and (indx % 1000) == 0:
                print >>self.fout, endFun+type+'\nbeginFunction\n'
                if self.xUniform == True:
                    print >>self.fout, g_indx, y, z
                else:
                    print >>self.fout, x, y, z
        print >>self.fout, endFun, type, '\n'
        return

#--- GetImage()
#
    def GetImage(self):
        flog = self.flog
        print >>self.fout, 'showpage\n'
        self.fout.flush()
        os.fsync(self.fout)
        if self.plotsPerPage == 1:
#            size = ' -g1200x550 '
            size = ' -g%dx%d ' % (self.xSize, self.ySize)
            xres = int(100 * self.xSize * 6.5 / (1200 * self.xLen))
            yres = int(110 * self.ySize / 550)
            res = ' -r%dx%d ' % (xres, yres)
            cmdStr = gsPath +' -sDEVICE=jpeg'+size+'-sOutputFile='+self.foutPath+self.foutName+'.jpg -dNOPAUSE '+ res +self.fname+' -c quit'
        else:
            size = ' -g1200x1100 '
            cmdStr = gsPath + ' -sDEVICE=jpeg'+size+'-sOutputFile='+self.foutPath+self.foutName+'%d.jpg -dNOPAUSE -r100x100 '+self.fname+' -c quit'
        print >>flog, 'cmdStr: ', cmdStr
        output = commands.getoutput(cmdStr)
        print >>flog, 'output from gs command: ', output
        return self.foutPath+self.foutName+'.jpg'


#--- Main
#
def main():

    tMin = 0
    tMax = 100000
    stateList = [0,1,2,2,3,3,3,3,4]
    fname = 'sched.txt'

    if len(sys.argv) == 2:
        fname = sys.argv[1]
    elif len(sys.argv) == 3:
        tMin = int(sys.argv[1])
        tMax = int(sys.argv[2])
    elif len(sys.argv) == 4:
        tMin = int(sys.argv[1])
        tMax = int(sys.argv[2])
        fname = sys.argv[3]
    elif len(sys.argv) != 1:
        print 'USAGE: psPlot.py [tMin tMax] [fname]'
        sys.exit(1)

    print 'tMin,tMax: ', tMin, tMax, 'fname: ', fname
    p = PsPlot('./p', 'Header', 'SubHeader', 1)
    fromStateList = []
    toStateList = []
    time1List = []
    time2List = []
    indx = 0
    oldTime = 0

    fin = open(fname, 'r')
    for inputLine in fin:
        inputLine = inputLine.replace(' ','')
        inputLine = inputLine.replace("'", '')
        i1 = inputLine.find('(')
        i2 = inputLine.find(')')
        inputList = inputLine[i1+1:i2-1].split(',')
        s1 = stateList[int(inputList[0])]
        s2 = stateList[int(inputList[1])]

        t = int(inputList[2])
        if indx != 0 and t >= tMin and t <= tMax:
            fromStateList.append(s1)
            toStateList.append(s2)
            time1List.append(oldTime)
            time2List.append(t)
        oldTime = t
        indx += 1

    p.SetPlot(tMin, tMax, 0, 0, 2, 0, 'Time', 'Socket/State', 'Chavey\'s Plot')

    state = 0
    while state <= 4:
        t1List = []
        t2List = []
        sList = []
        indx = 0
        for s in toStateList:
            if s == state:
                t1List.append(time1List[indx])
                t2List.append(time2List[indx])
                sList.append(0.10 + s*0.20)
            indx += 1
        p.PlotData(1,t1List, t2List, sList, 'Test',
                   '0.1 in  0 '+p.SetColor(p.colors[state])+' plotWbarsC',
                   sys.stdout)
        state += 1

    image = p.GetImage(sys.stdout)
    print 'Image file: ', image
    p.End()

if __name__ == "__main__":
    main()
