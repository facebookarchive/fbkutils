#!/usr/bin/python

import sys
import random
import os.path
import psPlot
import commands
import math
import shutil
import threading
import time
import os
import cgi
import cgitb; cgitb.enable()
import socket
from string import Template

# Globals
#
# The program can be used interactively as a web program,
# in which case it needs to be installed in cgi-exec directory,
# or in batch mode where it reads commands through a script
#Mode = 'web'
Mode = 'script'

Path = '.'
relPath = '.'
IterFile = 'exp.html'
menuState = ''
hostName = socket.gethostname()
ran = random.randrange(10000000)
#foutPath = '/Library/WebServer/Documents/Exp/tmp'
foutPath = 'tmp/'
foutName = str(ran)
lastVer=123456789
lastExp= 100.0
lastColorFieldVal = None
uploadDir = 'tmp/'
csvFilename = ''
iterName = 'exp'
iterIndex = 999999999
iterDict = {}
fieldList = []
fieldDict = {}
formatFlag = False
formatList = []
defaultFormatFlag = False
defaultFormat = 2
showColFormattingFlag = False
CommandDict = {}
CommandDict['rowColorChange'] = ''
SelectedRowList = []
SelectedColList = []
SelectedColDict = {}
SelectAllColsFlag = False
SelectAllRowsFlag = False
image = ''

Rows = []
Cols = []
if Mode == 'web':
  flog = open('log/log'+foutName+'.out', 'w')
else:
#  flog = open('/dev/null', 'w')
  flog = open('exp.log', 'w')
fieldDict = {}
formatList = []

saveIgnoreDict = {}
defaultVals = {}
History = []
SelectList = []
AveragedRows = []
AveragedRowsCount = []
ReadRowList = []

ReadCommandDict = {}
ReadCommands = 0

Y1minFlag = False
Y2minFlag = False
Y1min = 'x'
Y2min = 'x'

PlotPercentFlag = 0
PlotRatioFlag = 0

#rowColorChangeVal = 'exp'
rowColorChangeVal = 'ca'

# Global list or Dict initialiation
#
saveIgnoreDict['Rows'] = 'x'
#saveIgnoreDict['Cols'] = 'x'
saveIgnoreDict['File'] = 'x'
saveIgnoreDict['Path'] = 'x'
saveIgnoreDict['SaveComs'] = 'x'
saveIgnoreDict['ReadCommands'] = 'x'
saveIgnoreDict['StartMacro'] = 'x'
saveIgnoreDict['EndMacro'] = 'x'
saveIgnoreDict['SaveMacro'] = 'x'
saveIgnoreDict['DoMacro'] = 'x'
saveIgnoreDict['SavingMacro'] = 'x'

defaultVals['Y1LogScale'] = 'Auto'
defaultVals['PlotRatio'] = 'Off'
defaultVals['BkgLevel'] = '0.8'
defaultVals['PlotPercent'] = 'Off'
#defaultVals['xUniform'] = 'On'
defaultVals['Y2LogScale'] = 'Auto'

#--- rmSpaces
def rmSpaces(s):
  oldS = s.strip()
  newS = oldS.replace(' ','')
  while len(oldS) != len(newS):
    oldS = newS
    newS = oldS.replace(' ','')
  return newS

#--- doError
def doError(msg):
  if Mode == 'web':
    sys.stdout.write('Content-type: text/html\n\n')
    sys.stdout.write('<HTML> <HEAD> <TITLE>'+'exp.py Error'+'</TITLE>\n')
    sys.stdout.write('</HEAD><BODY><TABLE BORDER=2 BGCOLOR="#CCFFCC" CELLPADDING=20> <TR> <TD>\n<p><h2>'+msg+'</h2></TD></TR></TABLE></BODY>')
    sys.stdout.write('</HTML>')
  else:
    print 'ERROR in exp.py: %s' % msg
  print >>flog, 'ERROR in exp.py: %s' % msg
  print >>flog, 'DONE'
  flog.close()
  sys.stdout.close()
  os._exit(0)

#--- isFloat
def isFloat(s):
  try: return (float(s),True)[1]
  except (ValueError, TypeError), e: return False

#--- floatCmp
def floatCmp(s1, s2):
  v1 = float(s1)
  v2 = float(s2)
  if v1 < v2:
    return -1
  elif v1 == v2:
    return 0
  else:
    return 1

#--- sortListCmp
def sortListCmp(s1, s2):
  if isFloat(s1[0]) and isFloat(s2[0]):
    v1 = float(s1[0])
    v2 = float(s2[0])
    if (v1 < v2):
      return -1
    elif v1 == v2:
      return 0
    else:
      return 1
  else:
    if s1[0] < s2[0]:
      return -1
    elif s1[0] == s2[0]:
      return 0
    else:
      return 1

#--- sortListRevCmp
def sortListRevCmp(s1, s2):
  if isFloat(s1[0]) and isFloat(s2[0]):
    v1 = float(s1[0])
    v2 = float(s2[0])
    if (v1 < v2):
      return 1
    elif v1 == v2:
      return 0
    else:
      return -1
  else:
    if s1[0] < s2[0]:
      return -1
    elif s1[0] == s2[0]:
      return 0
    else:
      return 1

#--- getFieldIndex
def getFieldIndex(s):
  if s in fieldDict:
    return fieldDict[s]
  return -1

#--- resetSelectedColDict()
def resetSelectedColDict():
  global SelectedColList, SelectedColDict

  SelectedColDict = {}
  for field in SelectedColList:
    SelectedColDict[field] = 1
  return

#--- formatFloat
def formatFloat(f):
  if f <= 10:
    rv = float(int(100.0*f))/100.0
  elif f <= 100:
    rv = float(int(100.0*f))/100.0
  elif f <= 1000:
    rv = float(int(10.0*f))/10.0
  else:
    rv = float(int(f))
  return rv

#--- writeSpaces
def writeSpaces(f, spaces, text=''):
  i = 0
  line = ''
  while i < spaces:
    i = i + 1
    line = line + '&nbsp '
  f.write(line+text)
  return

#--- writeText
def writeText(f, text, spaces):
  writeSpaces(f,spaces,text)
  return

#--- writeHiddenInput
def writeHiddenInput(f, name, value):
  f.write('<input type="hidden" name="'+name+'" value="'+value+'">\n')
  return

#--- writeSelectInput
def writeSelectInput(f, label, name, values, selection, spaces, newLine, redoFlag, helpText=''):
  writeSpaces(f,spaces,label)
  f.write('<SELECT NAME="'+name+'" ')
  if redoFlag:
    f.write('onchange="redo()" ')
  if helpText != '':
    f.write('onmouseover="popup(\''+helpText+'\')" onmouseout="popdown()" onclick="popdown()" ')
  f.write('>')
  valuesList = values.split(',')
  for v in valuesList:
    vList = v.split('=')
    if name in ReadCommandDict and ReadCommandDict[name] == vList[0]:
      selStr = 'SELECTED'
    elif selection == vList[0]:
      selStr = 'SELECTED'
    else:
      selStr = ''
    f.write(' <OPTION VALUE="'+vList[0]+'" '+selStr+'>'+vList[1])
  f.write(' </SELECT>')
  if newLine != 0:
    f.write('\n')
  return

#--- writeCheckboxInput
def writeCheckboxInput(f, label, name, value, newLine, callFlag, helpText=''):
  if label != '':
    f.write('&nbsp ' + label)
  f.write('<input type=checkbox name="'+name+'" ')
  if name in ReadCommandDict  and  value == '':
    value = ReadCommandDict[name]
  if value != ''  and  value != 'F' and value != 'f':
    f.write('CHECKED ')
  if callFlag:
    f.write('onclick="redo()" ')
  if helpText != '':
    f.write('onmouseover="popup(\''+helpText+'\')" onmouseout="popdown()" ')
  if newLine != 0:
    f.write('>\n')
  else:
    f.write('>')
  return

#--- writeTextInput
def writeTextInput(f, label, name, value, size, spaces, newLine, helpText=''):
  writeSpaces(f,spaces,label)
  f.write('<input type=text name="'+name+'" ')
  if name in ReadCommandDict:
    value = ReadCommandDict[name]
  if value != '':
    f.write('value="'+value+'" ')
  if size != 0:
    f.write('size="'+str(size)+'" ')
  if helpText != '':
    f.write('onmouseover="popup(\''+helpText+'\')" onmouseout="popdown()" onclick="popdown()" ')
  if newLine != 0:
    f.write('>\n')
  else:
    f.write('>')
  return

#--- writeButton
def writeButton(f, label, name, size, spaces, helpText=''):
  writeSpaces(f,spaces)
  f.write('<input type="submit" name="'+name+'" value="'+label+'"')
  if size > 0:
    f.write(' size="'+str(size)+'" ')
  if helpText != '':
    f.write('" onmouseover="popup(\''+helpText+
            '\')" onmouseout="popdown()"')
  f.write(' >\n')
  return

#--- writeInputFile
def writeInputFile(f, label, name, accept, spaces, helpText=''):
  writeSpaces(f,spaces,label)
  f.write('<input type="file" name="'+name+'"')
  if helpText != '':
    f.write('" onmouseover="popup(\''+helpText+
            '\')" onmouseout="popdown()" onclick="popdown()" ')
  f.write('/>\n')
  return

#--- strFloatCmp
def strFloatCmp(s1, s2):
	v1 = float(s1)
	v2 = float(s2)
	return cmp(v1,v2)

#--- strIntCmp
def strIntCmp(s1, s2):
  i1 = int(s1)
  i2 = int(s2)
  return cmp(i1,i2)

#--- getFields
def getFields(line):
  global defaultFormatFlag, defaultFormat

  k=0
  if line.find(':') > 0 or defaultFormatFlag:
    formatFlag = True
    fieldList = []
    ffList = line.split(',')
    for field in ffList:
      ff = field.split(':')
      fieldList.append(ff[0])
      if len(ff) > 1:
        formatList.append(int(ff[1]))
      else:
        formatList.append(defaultFormat)
      fieldDict[ff[0]] = k
      k = k + 1
  else:
    formatFlag = False
    fieldList = line.split(',')
    for f in fieldList:
      fieldDict[f] = k
      k = k + 1
  print >> flog, 'Field List'
  print >>flog, fieldList
  print >>flog, '\nField Dict'
  print >>flog, fieldDict
  if formatFlag:
    print >>flog, 'Format List'
    print >>flog, formatList
  return fieldList, fieldDict, formatFlag, formatList

#--- myOpen
def myOpen(fname, type):
  print >>flog, 'Opening:', fname, ', Type:', type
  return open(fname, type)

#--- readCsvFile
def readCsvFile(fname):
  global flog, iterName, Rows, iterDict
  global fieldDict, fieldList, formatFlag, formatList
  global ReadRowList, SelectedRowList, SelectedColList, iterIndex

  print >>flog, 'readCsvFile: ' + fname
  if not os.path.exists(fname):
    doError('csv file "'+fname+'" does not exist')
  f = myOpen(fname, 'r')
  count=-1
  Rows = []
  ReadRowList = []
  iterDict = {}
  for iline in f:
    print >>flog, iline
    line = iline.strip()
    if len(line) == 0:
      continue
    if line[0] != '#':
      if count == -1:
        fieldList, fieldDict, formatFlag, formatList  = getFields(line)
        if iterName in fieldDict:
            iterIndex = fieldDict[iterName]
        else:
            iterIndex = fieldDict['exp']
            iterName = 'exp'
        print >>flog, "readCsvFile, iterIndex:", iterIndex
      else:
        rowList = line.split(',')
        print >>flog, rowList
        iterDict[rowList[iterIndex]] = count
        Rows.append(rowList)
      count += 1
    elif line[0:6] == '#Path:':
      Path = line[6:]
  f.close()
  for r in Rows:
    ReadRowList.append(r[iterIndex])
  SelectedRowList = ReadRowList*1
  SelectedColList = fieldList*1
  resetSelectedColDict()
  return

#--- appendCsvFile
def appendCsvFile(fname):
  global iterName, fieldList, fieldDict, iterDict, Rows

  if not os.path.exists(fname):
    doError('csv file "'+fname+'" does not exist')
  fout = myOpen(fname, 'r')
  count = -1
  print >>flog, 'appendCsvFile: ', fname
  iterIndex = fieldDict[iterName]
  for iline in fout:
    print >>flog, iline
    line = iline.strip()
    if len(line) == 0  or line[0] == '#':
      continue;
    if count == -1:
      fieldListNew,fieldDictNew,formatFlagNew,formatListNew  = getFields(line)
      count = len(Rows) - 1
      if not iterName in fieldDictNew:
        doError('csv file "'+fname+'" does not have an "'+iterName+'" column.')
      maxIter = 0
      for i in iterDict.keys():
        if int(i) > maxIter:
          maxIter = int(i)
      maxIter = int((maxIter+100)/100)*100
      iterIndexNew = fieldDictNew[iterName]
    else:
      rowList = line.split(',')
      print >>flog, rowList
      iterNew = str(int(rowList[iterIndexNew]) + maxIter)
      iterDict[iterNew] = count
      rowListNew = []
      for f in fieldList:
        if f in fieldDictNew:
          if f == iterName:
            rowListNew.append(iterNew)
          else:
            rowListNew.append(rowList[fieldDictNew[f]])
        else:
          rowListNew.append(' ')
      Rows.append(rowListNew)
    count += 1
#    elif line[0:6] == '#Path:':
#      Path = line[6:]
  fout.close()
  return

#--- getHex
def getHex(s):
  d = ord(s[0])
  if d <= ord('9'):
    rv = d - ord('0')
  elif d <= ord('Z'):
    rv = d - ord('A') + 10
  else:
    rv = d - ord('a') + 10
  return rv

#--- replaceHex
def replaceHex(line):
  i = line.find('%')
  n = 0
  while i >= 0 and n < 100000:
    c = chr(getHex(line[i+1])*16 + getHex(line[i+2]))
    line = line[0:i] + c + line[i+3:]
    j = line[i+1:].find('%')
    if j >= 0:
      i = i + 1 + j
    else:
      i = -1
    n = n + 1
  return line

#--- getSelectedRowsNOT
def getSelectedRowsNOT(line):
  SelectedRowList = []
  commandList = line.split(' ')
  for com in commandList:
    if com.startswith('Rows='):
      r = com.split('=')
      SelectedRowList.append(r[1])
  return SelectedRowList

#--- putHtmlHeader
def putHtmlHeader(fout, fieldList, formatFlag, formatList, colFormatFlag, foutName, title, image):
  global iterName

  htmlHeader = [
      '<HTML> <HEAD> <TITLE>'+title+' </TITLE> \n',
      '<STYLE TYPE="text/css">\n',
      'ul {list-style-type:none;margin:0;padding:0;overflow:hidden;}\n',
      'li {float:left;}\n',
      '<!--\n#pop {POSITION:absolute;VISIBILITY:hidden;border:1px solid mediumblue;Z-INDEX:200;}\n',
#      '//-->\n',
#      '<!--\n',
      '#fileWin {POSITION:absolute;VISIBILITY:hidden;Z-INDEX:198;}\n',
      '//-->\n',
      '</STYLE>\n',
      '</HEAD> \n'
  ]
  htmlHeader2 = [
      '<BODY>\n',
      '<DIV ID="pop"></DIV>\n',
      '<DIV ID="fileWin"></DIV>\n',
      '<SCRIPT TYPE="text/javascript">\n<!--\n',
      'var skn, sknTimer, fileObj, menuState="",menuTimer;\n',
      'var ns6=document.getElementById&&!document.all\n',
      'if (ns6)\n',
      'skn=document.getElementById("pop").style;\n',
      'skn.visibility="visible"\nskn.display="none";\n',
      'fileObj=document.getElementById("fileWin").style;\n',
      'fileObj.visibility="visible"\nfileObj.display="none";\n',
      'document.onmousemove=get_mouse;\n\n',
      'menuTimer=setTimeout("initMenu()",50);\n',
      # -- function showSkn
      'function showSkn() {\n',
      'skn.display=\'\'\n',
      '}\n',
      # -- function popup
      'function popup(msg) {\n',
      'var content="<TABLE WIDTH=400 BGCOLOR=\'lightblue\'><TD>"+msg+"</TD></TABLE>";\n',
      'var allowPopup;\n',
      'allowPopup=document.getElementsByName("HelpBubble").item(0).value\n',
      'if(ns6 && allowPopup=="on"){\n',
      'document.getElementById("pop").innerHTML=content\n',
#      'skn.display=\'\'\n',
      'sknTimer=setTimeout("showSkn()",1000);\n',
      '}\n',
      '}\n\n',
      # -- function mouse_over
      'function mouse_over(id) {\n',
#      'alert("mouseOver");\n',
      'document.getElementById(id).style.color="black"\n',
      '}\n',
      # -- function mouse_out
      'function mouse_out(id) {\n',
#      'alert("mouseOver");\n',
#      'document.write("mouse_out");\n',
      'if (menuState!=id) {\n',
      'document.getElementById(id).style.color="white"\n',
      '}\n}\n',
      # -- function initMenu
      'function initMenu() {\n',
      'var mid=document.getElementsByName("Menu").item(0).value;\n',
      'mouse_over(mid);\n',
      'on_click(mid);\n',
      '}\n',
      # -- function on_click
      'function on_click(id) {\n',
#      'alert("on_click, id="+id+", menuState="+menuState);\n',
      'if(id!=menuState && menuState!="") {\n',
      'document.getElementById(menuState).style.background="#98bf21";\n',
      'document.getElementById(menuState).style.color="white";\n',
      'document.getElementById(menuState+"Table").style.display="none"\n',
      '}\n',
      'menuState=id;\n',
      'document.getElementsByName("Menu").item(0).value=id;\n',
      'document.getElementById(id).style.background="#ccffcc"\n',
      'var idTable=id+"Table";\n',
#      'var msg=document.getElementById(idTable).innerHTML;\n',
#      'alert("on_click, msg="+msg);\n',
      'drawTable(idTable);\n',
#      'alert("mouse click end, menuState="+menuState);\n',
      '}\n',
      # -- function drawFile
      'function drawTable(idTable) {\n',
#      'var content="<TABLE WIDTH=760 BGCOLOR=\'#ccffcc\'><TD>"+msg+"</TD></TABLE>";\n',
#      'document.getElementById("fileWin").innerHTML=content;\n',
#      'fileObj.left=8;\nfileObj.top=33;\n',
#      'alert("drawFile0");\n',
      'var tableObj=document.getElementById(idTable).style;',
#      'alert("drawFile1");\n',
#      'tableObj.left=0;tableObj.top=0;\n',
      'tableObj.display=\'\';\n',
#      'alert("drawFile2");\n',
#      'fileObj.display=\'\';\n',
      '}\n',
      # -- function get_mouse
      'function get_mouse(e) {\n',
      'var x=(ns6)?e.pageX:event.x+document.body.scrollLeft;\n',
      'var rs=event.x+400;\n',
      'if (rs > document.body.clientWidth) x=x-(rs-document.body.clientWidth+7);\n'
      'skn.left=x;\n',
      'var y=(ns6)?e.pageY:event.y+document.body.scrollTop;\n',
      'skn.top=y+20;\n',
      '}\n',
      # -- function popdown
      'function popdown() {\n',
      'if (ns6)\n',
      'skn.display="none";\n',
      'clearTimeout(sknTimer);\n',
      '}\n',
      # -- function redo
      'function redo() {\n',
      '  document.table.submit()\n',
      '}\n',
      # -- function timedRefresh
      'function timedRefresh(timeoutPeriod) {\n',
      '  setTimeout("location.reload(true);", timeoutPeriod);\n',
      '}\n',
      '//-->\n</SCRIPT>\n',
#      '<BODY onload="JavaScript:timedRefresh(60000);">\n',
#      '<DIV ID="pop"></DIV>\n',
#      '<DIV ID="fileWin"></DIV>\n',

#      '<FORM name="table" method="post" action="http://'+hostName+'/cgi-bin/exp.py" enctype="multipart/form-data">\n',
			'<FORM name="table" method="post" action="http://localhost/Exp/cgi-exec/exp.py" enctype="multipart/form-data">\n',
#     enctype="multipart/form-data"
#     enctype="text/plain"
      ]

  for line in htmlHeader:
    fout.write(line)

  if (not 'SaveStatic' in CommandDict) or (not CommandDict['SaveStatic']):
    for line in htmlHeader2:
      fout.write(line)
  else:
    fout.write('<br>\n')

  ioHelpDict = {
      'file':
       'Commands that read or write files',
      'select':
       'Commands that remove rows or columns',
      'calc':
       'Commands that modify the spreadsheet',
      'plotting':
       'Commands to plot data in the spreadsheet',
      'settings':
       'Commands to set display options',
      'KeepRows':
       'Select rows by clicking on the checkbox on the left of the row, '
       'then press the button to remove the rows that are not selected. '
       'To recover deleted rows, press the <b>Back</b> browser button.',
      'DeleteRows':
       'Select rows by clicking on the checkbox on the left of the row, '
       'then press the button to remove the rows that are selected',
      'AllRows':
       'Selects all rows in the spreadsheet, then you can unselect some '
       'before further action',
      'KeepCols':
       'Select columns by clicking on the checkbox on the top of the column, '
       'then press the button to remove the columns thar are not selected.',
      'DeleteCols':
       'Select columns by clicking on the checkbox on the top of the column, '
       'then press the button to remove the columns that are selected',
      'AllCols':
       'Selects all columns in the spreadsheet, then you can unselect some '
       'before further action',
      'HelpBubble':
       'If checked show help bubble when the curson is on top of the frame '
       'elements',
      'ShowColFormatting':
       'When set, shows on the top of each column the number of decimal '
       'digits that will be shown for that column. You can also change it, '
       'the choices are 0, 1, 2, 3 or 4 decimal digits.',
      'SaveCommands':
       'Save current form state under the name entered in the '
       'text box',
      'ReadCommands':
       'Read form state from previously saved state under the name '
       'entered in the text box',
      'BrowseCommands':
       'Show a list of names for previously saved form states',
      'SavePage':
       'Save current page under the name specified in the text box. '
       'Use Browse Saved Pages to load a previously saved page.',
      'SaveStatic':
        'Page is saved without the commands header. Good for putting on '
        'any web server.',
      'ReadPage':
       'Show directory of experiments with saved pages',
      'csvFile':
       'Select a csv file to read. The first row should contain the '
       'column names. Each column name can optionally be followed by '
       'a colon and a digit thar represents the number of decimal '
       'places to use for that column in the spreadsheet.',
      'loadCsvFile':
       'Reload spreadsheet with the selected csv file.',
      'AppendCsvFile':
       'Append the selected csv file to the spreadsheet.',
      'Select':
       'Select rows that match the selection criteria.<br />'
       '<b>Examples:</b><br />'
       '1) &nbsp&nbsp ca==cubic,buffers==1.2;rtt==3,exp<>0:11<br />'
       'Matches all rows where (column <i>ca</i> equals <i>cubic</i> and '
       'column <i>buffers</i> equals <i>1.2</i>) or (column <i>rtt</i> '
       'equals <i>3</i> and (column <i>exp</i> > 0 and < 11) <br />'
       '2) &nbsp&nbsp exp[has].0<br />'
       'Matches all rows where column <i>exp</i> has the substring <i>.0</i><br />'
       '<b>The input should be of the form:</b><br />'
       '&nbsp&nbsp [&lt col_name &gt&lt op &gt&lt value &gt[&lt separator &gt]]+<br />'
       '<b>Where:</b><br />'
       '&nbsp&nbsp &lt col_name &gt is the name of a column <br />'
       '&nbsp&nbsp &lt op &gt is one of ==, !=, &lt;, &lt;=, &gt;, &gt;=, &lt;&gt;, [has], [hasnot]<br />'
       '&nbsp&nbsp &lt value &gt is a number or a string <br />'
       '&nbsp&nbsp &lt separator &gt is one of:<br />'
       '&nbsp&nbsp&nbsp&nbsp , &nbsp acts as AND<br />'
       '&nbsp&nbsp&nbsp&nbsp ; &nbsp acts as OR (lower precedence)',
      'AverageBy':
       'Average rows based on the column names in the text box. <br />'
       'The resulting '
       'spreadsheet will have one row for each combination of unique values '
       'in each of the specified column names. The values of the other '
       'columns in the spreadsheet will be the average of all the rows '
       'that have the same values in the specified column names (if the '
       'column has numerical values)<br />'
       'Appending [int] to a column name in the text box results in only '
       'comparing the integer component of the column values<br />'
       '<b>Note:</b> A new column will be added at the end showing the '
       'number of rows that was used in the average<br />'
       '<b>For example</b>, if column <i>ca</i> has two values: '
       '<i>bic</i> and '
       '<i>cubic</i> and column <i>buffers</i> has two values: <i>1.2</i> '
       'and <i>0.175</i> then the '
       'resulting spreadsheet will have 4 rows (2*2)',
      'Sort':
       'Sort in increasing order by the specified column names. To sort in '
       'decreasing order, add a <b>-</b> before the column name',
      'Description':
       'Create new <i>Descript</i> entries consisting of the fields entered '
       'in the text box (separated by commas) followed by its value for '
       'that row. '
       'For example, if we have a spreadsheet with ca==cubic and '
       'buffers==1.2 in the first row and ca==bic and buffers==0.175 '
       'in the second row then '
       'if <i>ca, buffers</i> is entered in the text box, '
       'the <i>Descript</i> column of the  new spreadsheet will have '
       '<i>cubic buffers==1.2</i> in the first row and '
       '<i>bic buffers==0.175</i> in the second row. Note that the column '
       'name is not used for column <i>ca</i> and <i>Notes</i>. '
       'This is useful when we want to plot more than one column '
       'together.',
      'ScaleColumns':
       'Scale the columns specified in the text box (separated by commas) '
       'by the scale factor specified in the <i>Factor</i> text box.',
      'ScaleFactor':
       'Scale the columns specified in the <i>Scale Columns</i> text box '
       '(separated by commas) '
       'by the scale factor specified in the <i>Scale Factor</i> text box.',
      'ScaleDo':
       'Scale the columns specified in the <i>Scale Columns</i> text box '
       '(separated by commas) '
       'by the scale factor specified in the <i>Scale Factor</i> text box.',
      'FilterNotes':
       'If string specified in text box is a substring of the value of '
       'the <i>Notes</i> column, then the value of the <i>Notes</i> '
       'column gets replaced with the input string; otherwise the '
       'value <i>Notes</i> column gets replaced with an empty string. '
       'This can be used to select rows based on a substring of the '
       'Notes by first doing a <i>Filter Notes</i> followed by a '
       '<i>Select</i>.',
      'PercentTable':
       'Create a display table using selected rows and columns. The first '
       'row in the display table is the first row in the current table and '
       'is displayed as is. Following rows are shown as relative percent '
       'change if the entries are numbers, left as is otherwise. If the '
       'entry in the top row is zero, corresponding entries in the following '
       'rows are shown as they are.',
      'NewColName':
       'Add a new column with the name specified in the text box, and whose '
       'value will be given by an operation (as specified in the drop '
       'down menu) applied to the two columns specified by their names',
      'NewColField1':
       'Column name of the first operand',
      'NewColOp':
       'Operation to apply to the two columns to create a new column'
       '& = string concatenation',
      'NewColField2':
       'Column name of the second operand',
      'Do':
       'Submit current form and apply changes to spreadsheet',
      'plotX':
       'Column name from where the X (horizontal) axis values will be taken. '
       'Note that if there is more than '
       'one row with the same value in this column, then bars in the graph '
       'will overlap unless separated by specifying a <i>Series</i>.',
      'plotY1':
       'Column name from where the Y1 (left vertical) axis values will be '
       'taken. These values are plotted with bars.',
      'plotY2':
       'Optional. Column name from where the Y2 (right vertical) axis values '
       'will be taken. These values are plotted with red diamonds.',
      'plotSeries':
       'Optional. Column name from where the series is created. '
       'When a series is '
       'specified, rather than plotting one bar (or diamond) per X value, '
       '<i>n</i> bars are plotted, where <i>n</i> is the number of unique '
       'values in the <i>series column</i>. For example, suppose we want '
       'to see the effect that buffer size has on losses for 3 TCP '
       'variants (Cubic, BIC and Reno). If we set X:ca (TCP variant), '
       'Y1:drops, and Series:buffers (buffer size, either 0.175 or 1.2 (MB)), '
       'then the X axis will '
       'have 3 lables: Cubic, BIC and Reno and for each label there will '
       'be two bars plotting the packet drops, one for a buffer size of '
       '175KB and the other for 1.2MB',
      'plotFilename':
       'The plot files will be saved under the specified name in Plot subdirectory',
      'plotXLen':
       'Lenght of X Axis in inches (default 6.5in)',
      'plotXSize':
       'Number of pixels in plot image in horizontal direction',
      'plotYSize':
       'Number of pixels in plot image in vertical direction',
      'plotDo':
       'Press this button after filling the appropriate plotting fields '
       'to insert a plot at the end of the spreadsheet.',
      'Y1min':
       'Optional. Specifies the minimum value of the Y1 axis. Otherwise '
       'the minimum value is chosen based on the data in the Y1 column.',
      'Y2min':
       'Optional. Specifies the minimum value of the Y2 axis. Otherwise '
       'the minimum value is chosen based on the data in the Y2 column.',
      'Y1div':
        'Optional. Divide Y1 coordinate by specified value.',
      'Y2div':
        'Optional. Divide Y2 coordinate by specified value.',
      'Y1eqY2':
       'Optional. Check it to make both Y axis the same.',
      'PlotPercent':
       'Writes the change (as percent) between the first bar and the other '
       'bars in a series. If the bars are wide, it is better to write it '
       'horizontally, otherwise vertically.',
      'PlotRatio':
       'Only used when <i>Write Percent</i> is off. Similar to <i>Write '
       'Percent</i>, but writes the ratio instead of the percent.',
      'xUniform':
       'Write the X axis labels with uniform spacing as opposed to the '
       'spacing determined by the X values. Check this if not all the '
       'values of the X axis are numbers.',
      'Y1LogScale':
       'Whether to use a logarithmic scale for the Y1 axis. The choices '
       'are: <i>auto</i> to set it automatically based on the range of '
       'values, <i>on</i> to use a log scale, or <i>off</i> to not use '
       'a log scale.',
      'Y2LogScale':
       'Whether to use a logarithmic scale for the Y2 axis. The choices '
       'are: <i>auto</i> to set it automatically based on the range of '
       'values, <i>on</i> to use a log scale, or <i>off</i> to not use '
       'a log scale.',
      'BkgLevel':
       'Optional. Set the grey level of the graph, where 0 is black and 1 '
       'is white.',
      'plotTitle':
       'Optional. Sets the main title of the graph. To have more than one '
       'Title line, separate them with a vertical bar.',
      'plotXTitle':
       'Optional. Sets the name of the X axis',
      'plotY1Title':
       'Optional. Sets the name of the Y1 (left vertical) axis.',
      'plotY2Title':
       'Optional. Sets the name of the Y2 (right vertical) axis.',
      'plotSeriesTitle':
       'Optional. Sets the name for the Series'
      }

  ioObjects = [

      ['menuBeg', "#98bf21"],
      ['menuButton', 'FILE', 'file', 150, 25],
      ['menuButton', 'SELECTION', 'select', 150, 25],
      ['menuButton', 'CALCULATION', 'calc', 150, 25],
      ['menuButton', 'PLOTTING', 'plotting', 150, 25],
      ['menuButton', 'SETTINGS', 'settings', 150, 25],
      ['menuEnd'],
      # -- fileTable
      ['text', '<TABLE BORDER=0 BGCOLOR="#ccffcc" id="fileTable" style="display:none;margin-top:-20px" width=760> <TR><TD>\n<p>', 1],
      ['textInput', 'Save Fields: ', 'SaveCommands', '', 25, 1, 0],
      ['textInput', 'Read Fields: ', 'ReadCommands', '', 25, 1, 0],
      ['button', 'Browse Saved Fields', 'BrowseCommands', 0, 1],
      ['eop', 1],
      ['textInput', 'Save Page: ', 'SavePage', '', 30, 1, 0],
      ['checkbox', 'Save Static', 'SaveStatic', False, 0],
      ['button', 'Browse Saved Pages', 'ReadPage', 0, 1],
      ['eop', 1],
      ['fileInput', 'New csv file: ', 'csvFile', 'text/csv', 1],
      ['button', 'Load File', 'loadCsvFile', 0, 1],
      ['button', 'Append File', 'AppendCsvFile', 0, 1],
      ['text', '</TD></TR></TABLE>', 1],
      # -- selectTable
      ['text', '<TABLE BORDER=0 BGCOLOR="#ccffcc" id="selectTable" style="display:none;margin-top:-20px" width=760> <TR> <TD>\n', 1],
      ['text', 'Rows: ', 1],
      ['button', 'Keep Selected', 'KeepRows', 0, 0],
      ['button', 'Delete Selected', 'DeleteRows', 0, 0],
      ['button', 'Select All', 'AllRows', 0, 0],
      ['eop', 1],
      ['text', 'Cols: ', 1],
      ['button', 'Keep Selected', 'KeepCols', 0, 0],
      ['button', 'Delete Selected', 'DeleteCols', 0, 0],
      ['button', 'Select All', 'AllCols', 0, 0],
      ['eop', 1],
      ['textInput', 'Select: ', 'Select', '', 60, 1, 0],
      ['text', '</TD></TR></TABLE>', 1],
      # -- calcTable
      ['text', '<TABLE BORDER=0 BGCOLOR="#ccffcc" id="calcTable" style="display:none;margin-top:-20px" width=760> <TR> <TD>\n', 1],
      ['textInput', 'Average By: ', 'AverageBy', '', 30, 1, 0],
      ['textInput', 'Sort: ', 'Sort', '', 20, 1, 0],
      ['eop', 1],
      ['textInput', 'Make Descript: ', 'Description', '', 25, 1, 0],
      ['textInput', 'Filter Notes: ', 'FilterNotes', '', 25, 1, 1],
      ['eop', 1],
      ['textInput', 'Scale Columns: ', 'ScaleColumns', '', 30, 1, 0],
      ['textInput', 'Scale Factor: ', 'ScaleFactor', '', 10, 1, 0],
      ['button', 'Do Scaling', 'ScaleDo', 0, 1],
      ['eop', 1],
      ['textInput', 'New Column: ', 'NewColName', '', 15, 1, 0],
      ['textInput', '=&nbsp', 'NewColField1', '', 15, 1, 0],
      ['selectInput', '', 'NewColOp', 'NewColDiv= / ,NewColMult= * ,'
       'NewColAdd= + ,NewColSub= - ,NewColConcat= & ', '', 1, 0, False],
      ['textInput', '', 'NewColField2', '', 15, 1, 1],
      ['button', 'Do', 'Do', 1, 1],
      ['eop', 1],
      ['button', 'Create Percent Table', 'PercentTable', 0, 1],
      ['text', '</TD></TR></TABLE>', 1],
      # -- plottingTable
      ['text', '<TABLE BORDER=0 BGCOLOR="#ccffcc" id="plottingTable" style="display:none;margin-top:-20px" width=760> <TR> <TD>\n', 1],
      ['textInput', 'Filename:', 'plotFilename', '', 16, 1, 1],
      ['textInput', 'X Len:', 'plotXLen', '6.5', 8, 1, 1],
      ['text', 'Plot size in Pixels ', 1],
      ['textInput', 'X:', 'plotXSize', '2400', 8, 1, 1],
      ['textInput', 'Y:', 'plotYSize', '1200', 8, 1, 1],
      ['button', 'Do Plot', 'plotDo', 0, 1],
      ['eop', 1],
      ['textInput', 'X:', 'plotX', '', 10, 1, 1],
      ['textInput', 'Y1:', 'plotY1', '', 10, 1, 1],
      ['textInput', 'Y2:', 'plotY2', '', 10, 1, 1],
      ['textInput', 'Series:', 'plotSeries', '', 10, 1, 1],
      ['eop', 1],
      ['textInput', 'Y1min:', 'Y1min', '',
       4, 1, 1],
      ['textInput', 'Y2min:', 'Y2min', '', 4, 1, 1],
      ['textInput', 'Y1div:', 'Y1div', '', 4, 1, 1],
      ['textInput', 'Y2div:', 'Y2div', '', 4, 1, 1],
      ['eop', 1],
      ['checkbox', 'Y1=Y2', 'Y1eqY2', False, 0],
      ['selectInput', 'Write Percent:', 'PlotPercent', 'Off=Off,'
          'Horizontal=Horizontal,Vertical=Vertical,Off=Off', '', 1, 1, False],
      ['selectInput', 'Write Ratio:', 'PlotRatio', 'Off=Off, Horizontal=Horizontal,'
       'Vertical=Vertical', '', 1, 1, False],
      ['eop', 1],
      ['checkbox', 'Even X labels:', 'xUniform', False, 1],
      ['selectInput', 'Y1 log scale:', 'Y1LogScale', 'Auto=Auto,Off=Off,On=On',
       '', 1, 0, False],
      ['selectInput', 'Y2 log scale:', 'Y2LogScale', 'Auto=Auto,Off=Off,On=On',
       '', 1, 0, False],
      ['textInput', 'Background:', 'BkgLevel', '0.8', 3, 1, 0],
      ['eop', 1],
      ['textInput', 'Title:', 'plotTitle',
       '', 30, 1, 1],
      ['textInput', 'X Title:', 'plotXTitle', '', 20, 1, 1],
      ['textInput', 'Y1 Title:', 'plotY1Title', '', 20, 1, 1],
      ['eop', 1],
      ['textInput', 'Y2 Title:', 'plotY2Title', '', 20, 1, 1],
      ['textInput', 'Series Title:', 'plotSeriesTitle', '', 20, 1, 1],
      ['text', '</TD></TR></TABLE>', 1],
      # -- settingsTable
      ['text', '<TABLE BORDER=0 BGCOLOR="#ccffcc" id="settingsTable" style="display:none;margin-top:-20px" width=760> <TR> <TD>\n', 1],
      ['checkbox', '<b>Enable Help Bubble (after 1 sec): </b>', 'HelpBubble', False, 0],
      ['eop', 1],
      ['checkbox', '<b>Show Column Formatting: </b>', 'ShowColFormatting',
       True, 1],
      ['eop', 0],
      ['textInput', '<b>Row Color Change:</b>', 'rowColorChange', rowColorChangeVal, 20, 1, 1],
      ['eop', 0],
      ['text', '<br /></TD></TR></TABLE>', 1],
      # -- Hidden inputs
      ['hidden', 'File', foutName],
      ['hidden', 'Path', Path],
			['hidden', 'relPath', relPath],
      ['hidden', 'IterFile', IterFile],
      ['hidden', 'Menu', menuState],
      ['hidden', 'Image', image],
      ]

  if (not 'SaveStatic' in CommandDict) or (not CommandDict['SaveStatic']):
    for obj in ioObjects:
      if len(obj) > 2 and obj[2] in ioHelpDict:
        helpStr = ioHelpDict[obj[2]]
      else:
        helpStr = ''
      if obj[0] == 'text':
        writeText(fout, obj[1], obj[2])
      elif obj[0] == 'button':
        writeButton(fout, obj[1], obj[2], obj[3], obj[4], helpStr)
      elif obj[0] == 'textInput':
        writeTextInput(fout, obj[1], obj[2], obj[3], obj[4], obj[5], obj[6],
                       helpStr)
      elif obj[0] == 'checkbox':
        if obj[2] in CommandDict:
          state = CommandDict[obj[2]]
        else:
          state = 'f'
        writeCheckboxInput(fout, obj[1], obj[2], state, obj[4], obj[3], helpStr)
      elif obj[0] == 'selectInput':
        writeSelectInput(fout, obj[1], obj[2], obj[3], obj[4], obj[5], obj[6], obj[7], helpStr)
      elif obj[0] == 'fileInput':
        writeInputFile(fout, obj[1], obj[2], obj[3], obj[4], helpStr)
      elif obj[0] == 'menuBeg':
        fout.write('<TABLE BORDER=0 BGCOLOR="'+obj[1]+'" cellspacing=0 '
                   'style="margin-bottom:0px"><TR>')
      elif obj[0] == 'menuEnd':
        fout.write('</TR></TABLE>\n')
      elif obj[0] == 'menuButton':
        fout.write('<TD width=%d height=%d align="center" id="%s" '
                   'onmouseover="mouse_over(\'%s\'),popup(\'%s\')" '
                   'onmouseout="mouse_out(\'%s\'),popdown()" '
                   'onclick="on_click(\'%s\')" style="color:white">\n' %
                   (obj[3],obj[4],obj[2],obj[2],helpStr,obj[2],obj[2]))
        fout.write('<font size=4>%s</font></TD>\n' % obj[1])
      elif obj[0] == 'hidden':
        writeHiddenInput(fout, obj[1], obj[2])
      elif obj[0] == 'eop':
        fout.write('</p>\n')
        if obj[1] > 0:
          fout.write('<p>')

  fout.flush()

# Write graph if there was a plot
  if image != ''  and   Mode == 'web':
    print >>flog, 'Write graph if there is a plot:"'+image+'"'
    fout.write('<p><IMG SRC="'+image+' "height="600" width="1200"></p>\n')

# Write spreadsheet header
  fout.write('<TABLE BORDER=1 style="margin-top:-18px">\n')
  fout.write('<TR BGCOLOR="#99CCF"> <TH> </TH>')

  if SelectAllColsFlag:
    checked = 'CHECKED'
  else:
    checked = ''

  indx = 0
  for f in fieldList:
    if (not 'SaveStatic' in CommandDict) or (not CommandDict['SaveStatic']):
      checkBox = '\n<br /><input type="checkbox" name="Cols" value="' + f + '" ' + checked + ' >'
    else:
      checkBox = ''

    if f in SelectedColList and SelectedColDict[f] == 1:
      if formatFlag:
        fv = str(formatList[indx])
      else:
        fv = ''
      if f == 'Notes':
        fout.write('<TH>Notes' + checkBox + '</TH>')
      elif f == 'Descript':
        fout.write('<TH>Descript' + checkBox + '</TH>')
      elif f == iterName or f == 'Exp':
        fout.write('<TH>' + f + '</TH>')
        #  fout.write('<TH>' + f + '<br /><br /></TH>')
      else:
        fout.write('<TH>' + f + checkBox )
        if showColFormattingFlag:
          fout.write('<br /> ')
          writeSelectInput(fout, '', 'colFormat_'+f, '0=0,1=1,2=2,3=3,4=4', fv, 0, 0, True,
                           'Decimal digits to show for numbers in this column')
        fout.write(' </TH>')
    indx += 1

  fout.write('</TR>\n')

# Specify colors for fields and line for Table rows
caColors = {'nv':'#F5DEB3', 'reno':'#B4EEB4', 'cubic':'#FFFFFF',
    'dctcp':'#EEE3FE', 'cdg':'#FEC0E0','pcecn':'#E3FEEE'}
lineColorField = 'ca'

rowColorDict = {'ca':caColors,
  'rtt':{'>0':'#C0C0FF'},
  'retransPkts%':{'>0':'#FF8080'},
  'localRetrans':{'>0':'#FF8080'},
  'retrans_total':{'>0':'#FF8080'},
  'meanLatency':{'>0':'#00C0C0'},
  'p99Latency':{'>0':'#00C0C0'},
  'rate':{'<ALL>':'#80FF80'}
}

#--- putHtmlTableRow
def putHtmlTableRow(fout, row, fieldList):
  global lastVer
  global lastExp
  global iterName
  global lastColorFieldVal

  print >>flog, 'in putHtmlTableRow: ', row

# Set row color
  color = '#C0C0C0'
  if lineColorField in fieldDict:
    indx = fieldDict[lineColorField]
    val = row[indx]
    colorDict = rowColorDict[lineColorField]
    if val in colorDict:
      color = colorDict[val]

# This feature changes the row color based on discontinuity,
# default is to change when there is a gap in 'exp' values
  if 'rowColorChange' in CommandDict:
    colorField = CommandDict['rowColorChange']
    print >>flog, 'rowColorChange in CommandDict, val:', colorField
  else:
    colorField = 'exp'

  boldFlag = False
  if colorField in fieldDict:
    if colorField == 'exp':
      if isFloat(row[fieldDict['exp']]):
        exp = float(row[fieldDict['exp']])
        if False and exp == int(exp):
          boldFlag = True
        else:
          boldFlag = False
        if math.fabs(exp - lastExp) > 1.5:
          color = '#00CC66'
        lastExp = exp
    else:
      colorFieldVal = row[fieldDict[colorField]]
      if lastColorFieldVal != None and colorFieldVal != lastColorFieldVal:
        color = '#00CC66'
      lastColorFieldVal = colorFieldVal

  if 'Ver' in fieldDict:
    ver = float(row[fieldDict['Ver']])
    if ver != lastVer:
      if lastVer != 123456789:
        color = '#00CC66'
      lastVer = ver
  iterIndex = fieldDict[iterName]

  if boldFlag:
    fout.write('<TR BGCOLOR="'+color+'" style="font-weight:bold">')
  else:
    fout.write('<TR BGCOLOR="'+color+'">')
  if SelectAllRowsFlag:
    checked = 'CHECKED'
  else:
    checked = ''
  if 'SaveStatic' in CommandDict and CommandDict['SaveStatic']:
    fout.write('<TD></TD>')
  else:
    fout.write('<TD><input type="checkbox" name="Rows" value="'+row[iterIndex]+'"'+checked+'></TD>')

  indx = 0
  for f in fieldList:
    if f in SelectedColList and SelectedColDict[f] == 1:
      val = row[indx]
      if formatFlag and isFloat(val):
        val = ('%.'+str(formatList[indx])+'f') % float(val)
      val = str(val)
      if boldFlag:
        fout.write('<b>')
      if f == iterName:
        if IterFile != '' and relPath != '':
          if 'SaveStatic' in CommandDict and CommandDict['SaveStatic'] and\
             Mode == 'web':
            fout.write('<TD><A HREF="./'+str(int(float(row[indx])))+'/'+IterFile+'">'+val+'</A></TD>')
          else:
            fout.write('<TD><A HREF="'+relPath+'/'+str(int(float(row[indx])))+'/'+IterFile+'">'+val+'</A></TD>')
        else:
          fout.write('<TD>'+val+'</TD>')
      elif f in rowColorDict:
        cellColor = None
        colDict = rowColorDict[f]
        if '<ALL>' in colDict:
          cellColor = colDict['<ALL>']
        elif '>0' in colDict and isFloat(val) and float(val) > 0:
          cellColor = colDict['>0']
        elif val in colDict:
          cellColor = colDict[val]
        if cellColor is not None:
          fout.write('<TD NOWRAP ALIGN=RIGHT BGCOLOR="' + cellColor +
              '">'+val+'</TD> ')
        else:
          fout.write('<TD NOWRAP ALIGN=RIGHT>' + val + '</TD> ')
      elif f == 'Notes':
        fout.write('<TD NOWRAP ALIGN=LEFT>'+val+'</TD> ')
      else:
        fout.write('<TD NOWRAP ALIGN=RIGHT>'+val+'</TD> ')
    indx += 1
  if boldFlag:
    fout.write('</b>')
  fout.write('</TR>\n')

#--- endHtml
def endHtml():
  sys.stdout.write('</BODY></HTML>\n')

#--- doEnd
def doEnd():
    endHtml()
    print >>flog, 'DONE'
    flog.close()
    sys.stdout.close()
    os._exit(0)

#--- percentTableWriteHeader
def percentTableWriteHeader(fout, fieldList):
  global iterName
  fout.write('<p><TABLE BORDER=3>\n<TR BGCOLOR="#BBBBBB"> ')
  for f in fieldList:
    if f == iterName:
      continue
    if f in SelectedColList and SelectedColDict[f] == 1:
      fout.write('<TH>'+f+'</TH> ')
  fout.write('</TR>\n')

#--- percentTableWriteRow
def percentTableWriteRow(fout, fieldList, Rows, indxTop, indxCur):
  global iterName
  fout.write('<TR BGCOLOR="#FFFFFF"> ')
  indx = 0
  for f in fieldList:
    if f == iterName:
      indx += 1
      continue
    if f in SelectedColList and SelectedColDict[f] == 1:
      if indxCur == indxTop:
        val = Rows[indxTop][indx]
        if isFloat(val):
          val = "%.1f" % float(val)
      else:
        if isFloat(Rows[indxTop][indx]):
          if (float(Rows[indxTop][indx]) == 0):
            val = Rows[indxCur][indx]
            if isFloat(val):
              val = "%.1f" % float(val)
          else:
            val = (float(Rows[indxCur][indx]) - float(Rows[indxTop][indx])) / float(Rows[indxTop][indx])
            if val > 0:
              sign = '+'
            else:
              sign = '-'
              val = -val
            val = "%6.1f" % (val*100)
            val = sign + str(val) + '%'
        else:
          val = Rows[indxCur][indx]
      fout.write('<TD>'+str(val)+'</TD> ')
    indx += 1
  fout.write('</TR>\n')

#--- removeEmptyFieldRows
def removeEmptyFieldRows(field):
  global SelectedRowlist

  newSelectedRowList = []
  for r in SelectedRowList:
    row = Rows[iterDict[r]]
    index = int(fieldDict[field])
    if row[index].strip() != '':
      newSelectedRowList.append(r)

  print >>flog, "removeEmptyFieldRows, newSelectedRowList: "
  print >>flog, newSelectedRowList
  return newSelectedRowList

#--- removeNonFloatFieldRows
def removeNonFloatFieldRows(field):
  global SelectedRowList

  print >>flog, "removeNonFLoatFieldRows, field:", field
  newSelectedRowList = []
  for r in SelectedRowList:
    row = Rows[iterDict[r]]
    useFlag = True
    index = int(fieldDict[field])
    print >>flog, "removeNonFloatFieldRows, index:", index, "len:", len(row)
    if isFloat(row[index]) or row[index] == '':
      newSelectedRowList.append(r)

  print >>flog, "removeNonFloatFielddRows, newSelectedRowList: "
  print >>flog, newSelectedRowList
  return newSelectedRowList


#--- getSelectedVals(field)
def getSelectedVals(field):
  vals = []
  if field in fieldDict:
    index = int(fieldDict[field])
    for r in SelectedRowList:
      row = Rows[iterDict[r]]
      if isFloat(row[index]):
        vals.append(float(row[index]))
      else:
        vals.append(0.111)
  return vals

#--- getSelectedStrings(field)
def getSelectedStrings(field):
  vals = []
  if field in fieldDict:
    index = int(fieldDict[field])
    for r in SelectedRowList:
      row = Rows[iterDict[r]]
      vals.append(row[index])
  return vals

#--- getSelectedSeriesVals(field, sField, sFieldVal)
def getSelectedSeriesVals(field,sField,sFieldVal):
  vals = []
  if field in fieldDict:
    index = int(fieldDict[field])
    if sField in fieldDict:
      sIndex = int(fieldDict[sField])
      for r in SelectedRowList:
        row = Rows[iterDict[r]]
        if row[sIndex] == sFieldVal:
          if isFloat(row[index]):
            vals.append(float(row[index]))
          else:
            vals.append(0.0)
  return vals

#--- getSelectedSeriesStrings(field, sField, sFieldVal)
def getSelectedSeriesStrings(field,sField,sFieldVal):
  vals = []
  if field in fieldDict:
    index = int(fieldDict[field])
    if sField in fieldDict:
      sIndex = int(fieldDict[sField])
      for r in SelectedRowList:
        row = Rows[iterDict[r]]
        if row[sIndex] == sFieldVal:
          vals.append(row[index])
  return vals

#--- getSelectedSeriesRows(sField, sFieldVal)
def getSelectedSeriesRows(sField,sFieldVal):
  rows = []
  if sField in fieldDict:
    sIndex = int(fieldDict[sField])
    for r in SelectedRowList:
      row = Rows[iterDict[r]]
      if row[sIndex] == sFieldVal:
        rows.append(row)
  return rows

#--- getTitles(xField, y1Field, y2Field)
#
def getTitle(xField, y1Field, y2Field):
  if 'plotXTitle' in CommandDict and CommandDict['plotXTitle'] != '':
    xTitle = CommandDict['plotXTitle']
  else:
    xTitle = xField
  if 'plotY1Title' in CommandDict and CommandDict['plotY1Title'] != '':
    y1Title = CommandDict['plotY1Title']
  else:
    y1Title = y1Field
  if 'plotY2Title' in CommandDict and CommandDict['plotY2Title'] != '':
    y2Title = CommandDict['plotY2Title']
  else:
    y2Title = y2Field
  if 'plotTitle' in CommandDict and CommandDict['plotTitle'] != '':
    mainTitle = CommandDict['plotTitle']
  else:
    mainTitle ='Plot of ' +  y1Field
    if y2Field != '':
      mainTitle = mainTitle + ' and ' + y2Field
  return mainTitle, xTitle, y1Title, y2Title

#--- setPlotVals
#
def setPlotVals(p):
  global PlotPercentFlag
  global PlotRatioFlag
  if 'plotXLen' in CommandDict:
    xlen = CommandDict['plotXLen']
    p.SetXLen(float(xlen))
  if 'plotXSize' in CommandDict:
    xsize = CommandDict['plotXSize']
    p.SetXSize(float(xsize))
  if 'plotYSize' in CommandDict:
    ysize = CommandDict['plotYSize']
    p.SetYSize(float(ysize))
  if 'BkgLevel' in CommandDict:
    bkgLevel = CommandDict['BkgLevel']
    level = float(bkgLevel)
    p.SetPlotBgLevel(level)
  if 'Y1LogScale' in CommandDict:
    value = CommandDict['Y1LogScale']
    p.SetPlotYLogScale(1,value)
  if 'Y2LogScale' in CommandDict:
    value = CommandDict['Y2LogScale']
    p.SetPlotYLogScale(2,value)
  if 'PlotPercent' in CommandDict:
    value = CommandDict['PlotPercent']
    print >>flog, 'PlotPercent: ', value
    if value != 'Off' and value != 'off':
      p.SetPlotPercentDir(value)
    else:
      PlotPercentFlag = 0
  if 'PlotRatio' in CommandDict:
    value = CommandDict['PlotRatio']
    print >>flog, 'PlotRatio: ', value
    if value != 'Off' and value != 'off' and PlotPercentFlag == 0:
      p.SetPlotPercentDir(value)
      PlotRatioFlag = 1
  print >>flog, 'PlotRatioFlag: ', PlotRatioFlag
  return

#--- scaleList
def scaleList(valList, div):
  print >>flog, "scaleList, div:", div, " valList:", valList
  if div == 0:
    return;
  i = 0
  while i < len(valList):
    valList[i] = float(valList[i]) / div
    i += 1
  print >>flog, "after scaling, valList:", valList
  return

#--- doUnits
def doUnits(units, divFlag, div, vmax, title):

  unitsList = units.split(',')
  orderedUnitsList = []
  for unit in unitsList:
    kv = unit.split('=')
    if len(kv) != 2:
      continue
    kv[0] = float(kv[0])
    if len(orderedUnitsList) == 0:
      orderedUnitsList.append(kv)
      print >>flog, '>>>> added to empty:', orderedUnitsList
    elif kv[0] < orderedUnitsList[-1][0]:
      orderedUnitsList.append(kv)
      print >>flog, '>>>> added at end:', orderedUnitsList
    else:
      for k in range(len(orderedUnitsList)):
        if kv[0] > orderedUnitsList[k][0]:
          orderedUnitsList = orderedUnitsList[:k] + [kv] + \
              orderedUnitsList[k:]
          print >>flog, '>>>> added at:'+str(k)+' OUL:', orderedUnitsList
          break
  print >>flog, '>>>> orderedUnitsList:', orderedUnitsList
  for kv in orderedUnitsList:
    print >>flog, '>>>>   comparing kv[0]:%.1f with max:%.1f' % (kv[0],vmax)
    if kv[0] < vmax:
      if divFlag:
        div *= kv[0]
      else:
        div = kv[0]
        divFlag = True
      title = title + ' (' + kv[1] + ')'
      vmax = vmax / div
      print >>flog, '>>>>   YES! div:%.1f, vmax:%.1f' % (div, vmax)
      break
  return divFlag, div, vmax, title

#--- doPlotSeries
#
def doPlotSeries(xField, y1Field, y2Field, sField, sList, sListNames):

  global flog
  global SelectedRowList

  print >>flog, 'doPlotSeries - xField:%s, y1Filed:%s, y2Field:%s, sField:%s'\
    % (xField, y1Field, y2Field, sField)
  mainTitle,xTitle,y1Title,y2Title = getTitle(xField,y1Field,y2Field)
  xValsList = []
  y1ValsList = []
  y2ValsList = []
  y3ValsList = []
  y3FieldFlag = False

  count = 0
  xVals = getSelectedStrings(xField)
  if 'xUniform' in CommandDict:
    xUniform = CommandDict['xUniform']
  else:
    xUniform = 'off'
  if xUniform == 'off' or xUniform == 'Off' or xUniform == 0:
    xUniformFlag = False
    for x in xVals:
      if not isFloat(x):
        xUniformFlag = True
        break
  else:
    xUniformFlag = True

  y2FieldList = y2Field.split(',')
  OrigSelectedRowList = SelectedRowList
  SelectedRowList = removeEmptyFieldRows(xField)
  SelectedRowList = removeNonFloatFieldRows(y1Field)
  for f in y2FieldList:
    if f != '':
      SelectedRowList = removeNonFloatFieldRows(f)

  if not xUniformFlag:
    xVals = getSelectedVals(xField)
  y1Vals = getSelectedVals(y1Field)
  y2Field = y2FieldList[0]
  y2Vals = getSelectedVals(y2Field)
  if len(y2FieldList) > 1:
    y3Field = y2FieldList[1]
    y3FieldFlag = True
    y3Vals = getSelectedVals(y3Field)
  else:
    y3Vals = []

  if 'Y1div' in CommandDict:
    y1divFlag = True
    y1div = float(CommandDict['Y1div'])
  else:
    y1divFlag = False
    y1div = 0
  if 'Y2div' in CommandDict:
    y2divFlag = True
    y2div = float(CommandDict['Y1div'])
  else:
    y2divFlag = False
    y2div = 0

#    scaleList(y1Vals, float(CommandDict['Y1div']))
#  if 'Y2div' in CommandDict:
#    scaleList(y2Vals, float(CommandDict['Y2div']))

# Set max and min values
  if 'Y1min' in CommandDict and isFloat(CommandDict['Y1min']):
    yMin = float(CommandDict['Y1min'])
    print >>flog, "Y1min=%s  yMin=%.2f" % (CommandDict["Y1min"], yMin)
  else:
    yMin = min(y1Vals)

  if 'Y2min' in CommandDict and isFloat(CommandDict['Y2min']):
    y2Min = float(CommandDict['Y2min'])
  else:
    y2Min = min(y2Vals)
  yMax = max(y1Vals)
  y2Max = max(y2Vals)
  if len(y3Vals) > 0:
    y3Min = min(y3Vals)
    y2Min = min([y2Min, y3Min])
    y3Max = max(y3Vals)
    y2Max = max([y2Max, y3Max])

  if 'Y1eqY2' in CommandDict and CommandDict['Y1eqY2'] == 'on':
    yMin = min([yMin, y2Min])
    y2Min = yMin
    yMax = max([yMax, y2Max])
    y2Max = yMax

  if 'Y1Units' in CommandDict:
    units = CommandDict['Y1Units']
    if units != '':
      y1divFlag, y1div, yMax, y1Title = doUnits(units, y1divFlag, y1div, yMax,
                                              y1Title)
    print >>flog, 'Y1Units, units="%s", y1div=%.2f, yMax=%.1f' % \
                  (str(units), y1div, yMax)

  if 'Y2Units' in CommandDict:
    units = CommandDict['Y2Units']
    if units != '':
      y2divFlag, y2div, y2Max, y2Title = doUnits(units, y2divFlag, y2div, y2Max,
                                               y2Title)

  print >>flog, 'zz sField: ', sField, ' sList: ', sList, ' len(sList): ', len(sList)

  if len(sList) == 0:
    numDataSets = 1
    if y1divFlag:
      scaleList(y1Vals, y1div)
    if y2divFlag:
      scaleList(y2Vals, y2div)
      if len(y3Vals) > 0:
        scaleList(y3Vals, y2div)

    xValsList.append(xVals)
    y1ValsList.append(y1Vals)
    y2ValsList.append(y2Vals)
    y3ValsList.append(y3Vals)
    count = 1
    xSet = set(xVals)
  else:
    numDataSets = len(sList)
    if y1divFlag:
      scaleList(y1Vals, y1div)
    if y1divFlag:
      scaleList(y2Vals, y2div)

    for val in sList:
      if xUniformFlag == True:
        valList = getSelectedSeriesStrings(xField, sField, sList[count])
      else:
        valList = getSelectedSeriesVals(xField, sField, sList[count])
      print >>flog, 'valList: ', valList
      xValsList.append(valList)
      if count == 0:
        xSet = set(valList)
      else:
        xSet.update(valList)

      valList = getSelectedSeriesVals(y1Field, sField, sList[count])
      if y1divFlag:
        print >>flog, 'y1divFlag is T, y1div:', y1div, ' valList:', valList
        scaleList(valList, y1div)
        print >>flog, '  after valList:', valList
      y1ValsList.append(valList)

      valList = getSelectedSeriesVals(y2Field, sField, sList[count])
      if y2divFlag:
        scaleList(valList, y2div)
      y2ValsList.append(valList)

      if y3FieldFlag:
        valList = getSelectedSeriesVals(y3Field, sField, sList[count])
        if y2divFlag:
          scaleList(valList, y2div)
        y3ValsList.append(valList)

      count += 1

  xValUniqueList = list(xSet)
  numFlag = False
  for x in xValUniqueList:
    if isFloat(x):
      numFlag = True
      continue
    else:
      numFlag = False
      break
  if numFlag:
    xValUniqueList.sort(floatCmp)
  else:
    xValUniqueList.sort()

  if len(xVals) == 0 or len(y1Vals) == 0:
    print >>flog, "len(xVals) == 0 or len(y1Vals) == 0"
    return ''
  print >>flog, '\ndoPlotSeries'
  print >>flog, 'xVals: ', xVals
  print >>flog, 'y1Vals: ', y1Vals
  print >>flog, 'y2Vals: ', y2Vals
  if y3FieldFlag:
    print >>flog, 'y3Vals: ', y3Vals
  print >>flog, 'xValsList: ', xValsList
  print >>flog, 'y1ValsList: ', y1ValsList
  print >>flog, 'y2ValsList: ', y2ValsList
  print >>flog, 'Calling psPlot.PsPlot'
  print >>flog, 'xSet: ', xSet
  print >>flog, 'xValUniqueList: ', xValUniqueList

  foutName = str(random.randrange(10000000))
  p = psPlot.PsPlot(foutPath+foutName, '', '', 1)
  p.flog = flog

  p.colors = [ (0,0,0.5), (0.5,0,0), (0.42,0.55,0.14),
               (0,0.5,0), (0.6,0.5,0.3), (0.6,0.2,0.8),
               (0.4,0.3,0.5), (0.5,0.5,0.5), (0.8,0.0,0.0), (0,0,0) ]
  p.colorsN = 10

  print >>flog, 'psPlot.PsPlot returns; foutPath: ',p.foutPath,' foutName: ', p.foutName
  setPlotVals(p)
  if len(sList) > 1 and 'plotSeriesTitle' in CommandDict:
    p.seriesTitle = CommandDict['plotSeriesTitle']

  if xUniformFlag == True:
    xMin = xValUniqueList
  else:
    xMin = min(xVals)
  if 'Y1min' in CommandDict  and isFloat(CommandDict['Y1min']):
    yMin = float(CommandDict['Y1min'])
  else:
    yMin = min(y1Vals)

  y23Vals = []
  for v in y2Vals:
    y23Vals.append(v)
  if y3FieldFlag:
    for v in y3Vals:
      y23Vals.append(v)
  print >>flog, 'y23Vals: ', y23Vals

  if len(y2Vals) == 0:
    p.SetPlot(xMin, max(xVals), 0, yMin, max(y1Vals), 0, xTitle, y1Title,
              mainTitle)
  else:
    if 'Y2min' in CommandDict  and isFloat(CommandDict['Y2min']):
      y2Min = float(CommandDict['Y2min'])
    else:
      y2Min = min(y2Vals)
    if 'Y1eqY2' in CommandDict and CommandDict['Y1eqY2'] == 'on':
      yMin = yMin
      if yMin > y2Min: yMin = y2Min
      yMax = max(y1Vals)
      if yMax < max(y23Vals): yMax = max(y23Vals)
      p.SetPlot2(xMin, max(xVals), 0, yMin, yMax, 0, yMin,
               yMax, 0, xTitle, y1Title, y2Title, mainTitle)
    else:
      p.SetPlot2(xMin, max(xVals), 0, yMin, max(y1Vals), 0, y2Min,
                 max(y23Vals), 0, xTitle, y1Title, y2Title, mainTitle)

#  if xUniformFlag == True:
#    xMin = xValUniqueList
#  else:
#    xMin = min(xVals)
#
#  if len(y2Vals) == 0:
#    p.SetPlot(xMin, max(xVals), 0, yMin, max(y1Vals), 0, xTitle, y1Title,
#              mainTitle)
#  else:
#
#
#    p.SetPlot2(xMin, max(xVals), 0, yMin, yMax, 0, y2Min,
#               y2Max, 0, xTitle, y1Title, y2Title, mainTitle)

  print >>flog, 'setPlot returns\nCalling PlotData'
  print >>flog, 'xLen: ', p.xLen, ' xCount: ', p.xCount, ' xInc: ', p.xInc
  if xUniformFlag == True:
    barWidth = 0.7*(p.xLen/p.xCount)/numDataSets
    xdMin = 1
  else:
    xdMin = xValUniqueList[1] - xValUniqueList[0]
    indx = 2
    while indx < len(xValUniqueList):
      t = xValUniqueList[indx] - xValUniqueList[indx-1]
      if t < xdMin:
        xdMin = t
      indx += 1
    barWidth = (p.xLen/p.xCount)*xdMin/p.xInc
    barWidth *= 0.7/numDataSets
  print >>flog, 'xdMin: ', xdMin
  print >>flog, 'barWidth: ', barWidth
  p.SeriesNames(sListNames)
  xf = xdMin*0.8/numDataSets
  xf0 = -xf*(numDataSets - 1)/2
  indx = 0
  while indx < numDataSets:
    print >>flog, 'Plotting ',indx,' xOffset: ', xf0
    print >>flog, '  xVals: ', xValsList[indx]
    p.xOffset = xf0
    xf0 += xf
    if len(y2Vals) == 0:
      p.PlotData(1, xValsList[indx], y1ValsList[indx], y1Field, '',
                 str(barWidth)+p.SetColor(p.colors[indx % p.colorsN])+
                 ' plotBarsC')
    else:
      p.PlotData(1, xValsList[indx], y1ValsList[indx], y1Field, '',
                 str(barWidth)+p.SetColor(p.colors[indx % p.colorsN])+
                 ' plotBarsC')
      if y3FieldFlag:
        p.PlotData(2, xValsList[indx], y3ValsList[indx], y3Field, '',
                   str(barWidth)+p.SetColor(p.colorWhite)+
                    ' plotBarsCline')
      p.PlotData(2, xValsList[indx], y2ValsList[indx], y2Field, '',
                 '6 '+p.SetColor(p.colorGreen)+
                 ' plotSymbolsC')
    if indx > 0 and PlotPercentFlag > 0:
      y0List = y1ValsList[0]
      y1List = y1ValsList[indx]
      y1PercentList = []
      k = 0
      for v in y0List:
        if v != 0 and xValsList[0][k] == xValsList[indx][k]:
          pval = (y1List[k]/v - 1.0)*100.0
          if pval < 0:
            pval += -0.5
          else:
            pval += 0.5
        else:
          pval = 0
        y1PercentList.append(pval)
        k += 1
      p.outputPS('1 1 1 setrgbcolor ')
      p.PlotData(0, xValsList[indx], y1PercentList, '', '',
                 '0 '+'.3'+' 12 plotNumPercent')
    elif PlotRatioFlag > 0:
      y1List = y1ValsList[indx]
      y2List = y2ValsList[indx]
      y1PercentList = []
      k = 0
      for v in y1List:
        if v != 0:
          pval = (y2List[k]/v - 1.0)*100.0
          if pval < 0:
            pval += -0.5
          else:
            pval += 0.5
        else:
          pval = 0
        y1PercentList.append(pval)
        k += 1
      p.outputPS('1 1 1 setrgbcolor ')
      p.PlotData(0, xValsList[indx], y1PercentList, '', '',
                 '0 '+'.3'+' 12 plotNumPercent')
    indx += 1

  image = p.GetImage()
  print >>flog, 'GetImage returns, file: ', image
  SelectedRowList = OrigSelectedRowList
  return image

#--- doPlot
def doPlot():

  global CommandDict
  global flog

  plotError = 0
  if 'plotX' in CommandDict:
    xField = CommandDict['plotX']
  else:
    plotError = 1
  if 'plotY1' in CommandDict:
    y1Field = CommandDict['plotY1']
  else:
    plotError = 2
  if 'plotY2' in CommandDict:
    y2Field = CommandDict['plotY2']
  else:
    y2Field = ''
  seriesFlag = False
  if 'plotSeries' in CommandDict:
    psList = (CommandDict['plotSeries']).split(';')
    seriesField = psList[0]
    if len(psList) > 1:
      seriesListTemp = psList[1].split(',')
      seriesListNames = []
      seriesList = []
      for s in seriesListTemp:
        sl = s.split('=')
        seriesList.append(sl[0])
        if len(sl) == 1:
          seriesListNames.append(sl[0])
        else:
          seriesListNames.append(sl[1])
    else:
      seriesList = []
      seriesListNames = []
    print >>flog, 'psList: ', psList, ' sField: ', seriesField,\
      ' sList: ', seriesList
    if seriesField in fieldDict:
      seriesFlag = True
      col = fieldDict[seriesField]
      seriesCol = col
      if len(seriesList) == 0:
        seriesDict = {}
        seriesCount = 0
        print >>flog, 'Series field: ', seriesField, ' index: ', col
        for r in SelectedRowList:
          indx = iterDict[r]
          row = Rows[indx]
          f = row[col]
          if f in seriesDict:
            pass
          else:
            seriesDict[f] = seriesCount
            seriesCount += 1
            seriesList.append(f)
        if seriesCount <= 1:
          seriesFlag = False
      print >>flog, 'seriesList: ', seriesList
      if len(seriesList) != len(seriesListNames):
        seriesListNames = seriesList
      i = 0
      for s in seriesListNames:
        s = s.replace('(','\(')
        s = s.replace(')','\)')
        seriesListNames[i] = s;
        i = i + 1
      print >>flog, 'seriesListNames: ', seriesListNames
  else:
    seriesField = ''
    seriesList = []
    seriesListNames = []
  print >>flog, 'SeriesFlag: ', seriesFlag
  if plotError > 0:
    print >>flog, '\n*** plotError: ', plotError
    return ''
  else:
    image = doPlotSeries(xField, y1Field, y2Field, seriesField,
                         seriesList, seriesListNames)
    print >>flog, 'doPlot image:', image
    if image == '':
      return image
    if 'plotFilename' in CommandDict and CommandDict['plotFilename'] != None:
      plotFn = CommandDict['plotFilename']
      if not os.path.exists('Plots'):
        os.mkdir('Plots', 0777)

      cmdStr = 'mv ' + image + ' Plots/' + plotFn + '.jpg'
      print >>flog, "doPlot, cmdStr: ", cmdStr
      output = commands.getoutput(cmdStr)
      print >>flog, 'output from cp plot file: ', output
      image = 'Plots/' + plotFn + '.jpg'
      CommandDict['plotFilename'] = None
  return image

#--- putImage
def putImage(image):
  sys.stdout.write('<p><IMG SRC="'+image+'"></p>\n')

#--- isEq
#
def isEq(a, b):
  if isFloat(a) and isFloat(b):
    if float(a) == float(b):
      return True
    else:
      return False
  if a == b:
    return True
  return False

#--- isNotEq
#
def isNotEq(a, b):
  if isFloat(a) and isFloat(b):
    if float(a) != float(b):
#      print >>flog, 'isNotEq 2 floats: ' + str(a) + ' & ' + str(b)
      return True
    else:
      return False
  if a != b:
    print >>flog, 'isNotEq NOT 2 floats: ' + str(a) + ' & ' + str(b)
    return True
  return False

#--- getSelectedRows(selectionStr, availableRows)
#
def getSelectedRows(selectionStr, availableRows):
  print >>flog, 'getSelectedRows( ', selectionStr, availableRows, ' )'
  localSelectList = selectionStr.split(",")
  SelectEQList = []
  SelectNEList = []
  SelectGTList = []
  SelectLTList = []
  SelectGEList = []
  SelectLEList = []
  SelectHasList = []
  SelectHasnotList = []
  SelectRangeList = []
  for selection in localSelectList:
    selection = selection.strip()
#    selection.replace(' ','')
    if selection.find('==') >= 0:
      SelectEQList.append(selection.split('=='))
    elif selection.find('!=') >= 0:
      SelectNEList.append(selection.split('!='))
    elif selection.find('>=') >= 0:
      SelectGEList.append(selection.split('>='))
    elif selection.find('<=') >= 0:
      SelectLEList.append(selection.split('<='))
    elif selection.find('<>') >= 0:
      SelectRangeList.append(selection.split('<>'))
    elif selection.find('>') >= 0:
      SelectGTList.append(selection.split('>'))
    elif selection.find('<') >= 0:
      SelectLTList.append(selection.split('<'))
    elif selection.find('[has]') >= 0:
      SelectHasList.append(selection.split('[has]'))
    elif selection.find('[hasnot]') >= 0:
      SelectHasnotList.append(selection.split('[hasnot]'))

  if len(localSelectList) > 0:
    localSelectedRowList = []
    for r in availableRows:
      useRow = 1
      indx = iterDict[r]
      row = Rows[indx]
      for sel in SelectEQList:
        if sel[0] in fieldDict:
          col = fieldDict[sel[0]]
          if isNotEq(row[col], sel[1]):
            useRow = 0
      for sel in SelectNEList:
        if sel[0] in fieldDict:
          col = fieldDict[sel[0]]
          if isEq(row[col], sel[1]):
            useRow = 0
      for sel in SelectHasList:
        if sel[0] in fieldDict:
          col = fieldDict[sel[0]]
          if sel[1][0] == '^':
            if row[col].find(sel[1][1:]) != 0:
              useRow = 0
          elif row[col].find(sel[1]) < 0:
            useRow = 0
      for sel in SelectHasnotList:
        if sel[0] in fieldDict:
          col = fieldDict[sel[0]]
          if sel[1][0] == '^':
            if row[col].find(sel[1][1:]) != 0:
              useRow = 0
          elif row[col].find(sel[1]) >= 0:
            useRow = 0
      for sel in SelectGTList:
        if sel[0] in fieldDict:
          col = fieldDict[sel[0]]
          if float(row[col]) <= float(sel[1]):
            useRow = 0
      for sel in SelectLTList:
        if sel[0] in fieldDict:
          col = fieldDict[sel[0]]
          if float(row[col]) >= float(sel[1]):
            useRow = 0
      for sel in SelectRangeList:
        if sel[0] in fieldDict:
          col = fieldDict[sel[0]]
          vals = sel[1].split(':')
          print >>flog, 'Range %s=%s, %s:%s' % (sel[0], row[col], vals[0], vals[1])
          if len(vals) == 2:
            if float(row[col]) <= float(vals[0]) or \
               float(row[col]) >= float(vals[1]):
              print >>flog, '  useRow = 0'
              useRow = 0
      for sel in SelectGEList:
        if sel[0] in fieldDict:
          col = fieldDict[sel[0]]
          if float(row[col]) < float(sel[1]):
            useRow = 0
      for sel in SelectLEList:
        if sel[0] in fieldDict:
          col = fieldDict[sel[0]]
          if float(row[col]) > float(sel[1]):
            useRow = 0
      if useRow > 0:
        localSelectedRowList.append(r)
    print >>flog, 'getSelectedRowList: ', localSelectedRowList
    return localSelectedRowList
  return []

#--- doSelect
def doSelect(selectString):
  global SelectedRowList

  print >>flog, 'doSelect, SelectedRowList:', SelectedRowList
  if selectString.lower() == 'all':
    SelectedRowList = ReadRowList*1
    return

  orSelectStrings = selectString.split(";")
  chosenRows = set([])
  selectedRowSet = set(SelectedRowList)
  for selectionStr in orSelectStrings:
    selectionStr = selectionStr.strip()
    availableRows = selectedRowSet - chosenRows
    chosenRows = chosenRows.union(set(getSelectedRows(selectionStr,
                                                      availableRows)))
  SelectedRowList = list(chosenRows)
  SelectedRowList.sort(floatCmp)

  print >>flog, 'New Selected List'
  print >>flog, SelectedRowList
  return

#--- doAverage
def doAverage(averageString):

  global AveragedRows
  global AveragedRowsCount
  global fieldDict
  global fieldList
  global SelectedColList
  global SelectedColDict
  global SelectedRowList
  global formatFlag
  global formatList
  global Rows
  global iterDict
  global iterName

  iterCol = fieldDict[iterName]
  averageList = averageString.split(",")
  averageColList = []
  averageFunList = []
  AveragedRows = []
  AveragedRowsCount = []

  for field in averageList:
    pos = field.find('[')
    if pos > 0 and field[-1] == ']':
      fieldFun = field[pos:]
      field = field[0:pos]
    else:
      fieldFun = None
    if field in fieldDict:
      col = fieldDict[field]
      averageColList.append(col)
      averageFunList.append(fieldFun)

  print >>flog, 'average List: '
  print >>flog, averageList
  print >>flog, 'average Col List: '
  print >>flog, averageColList
  print >>flog, 'average Fun List: '
  print >>flog, averageFunList

  if not 'avgCnt' in fieldDict:
    fieldDict['avgCnt'] = len(fieldList)
    fieldList.append('avgCnt')
    SelectedColList.append('avgCnt')
    SelectedColDict['avgCnt'] = 1
    if formatFlag:
      formatList.append(int(0))
    for row in Rows:
      row.append('1')

  avgCnt_indx = fieldDict['avgCnt']
  for r in SelectedRowList:
    indx = iterDict[r]
    row = Rows[indx]
    aRowNum = 0
    match = 0
    for aRow in AveragedRows:
      match = 1
      indx = -1
      for col in averageColList:
        indx += 1
        if averageFunList[indx] == None:
          if isNotEq(row[col], aRow[col]):
            match = 0
        elif averageFunList[indx] == '[int]':
          newVal = row[col]
          avgVal = aRow[col]
          if not isFloat(newVal) or not isFloat(avgVal):
            match = 0
          else:
            newVal = int(float(newVal))
            avgVal = int(float(avgVal))
            if newVal != avgVal:
              match = 0
        elif averageFunList[indx].find('[has:') >= 0:
          pos = averageFunList[indx].find('[has:')
          hasStr = averageFunList[indx][pos+5:-1]
          if hasStr[0] == '^':
            hasStr = hasStr[1:]
            newHas = (row[col].find(hasStr) == 0)
            avgHas = (aRow[col].find(hasStr) == 0)
          else:
            newHas = (row[col].find(hasStr) >= 0)
            avgHas = (aRow[col].find(hasStr) >= 0)
          if newHas != avgHas:
            match = 0
      if match == 1:
        print >>flog, 'Matched Averaged Row: ' + str(row[iterCol]) + ' with: ' + str(aRow[iterCol])
        colNum = 0
        AveragedRowsCount[aRowNum] += 1
        for colVal in row:
          if colNum >= 3 and (not colNum in averageColList) and isFloat(colVal) and isFloat(AveragedRows[aRowNum][colNum]):
            AveragedRows[aRowNum][colNum] = float(AveragedRows[aRowNum][colNum]) + float(colVal)
          elif AveragedRows[aRowNum][colNum] != colVal:
            if colNum != iterCol:
              AveragedRows[aRowNum][colNum] = '...'
          colNum += 1
        break
      aRowNum += 1
    if match == 0:
      AveragedRows.append(row)
      AveragedRowsCount.append(1)
      print >>flog, 'New Averaged Row: ' + row[iterCol]
  aRowNum = 0
  for aRow in AveragedRows:
    colNum = 0
    for colVal in aRow:
      if colNum >= 3 and (not colNum in averageColList) and \
         isFloat(AveragedRows[aRowNum][colNum]) and colNum != avgCnt_indx:
        if formatFlag:
          AveragedRows[aRowNum][colNum] = float(AveragedRows[aRowNum][colNum])\
                                          /  AveragedRowsCount[aRowNum]
        else:
          AveragedRows[aRowNum][colNum] = formatFloat(float(AveragedRows[aRowNum][colNum]) /  AveragedRowsCount[aRowNum])
      elif colNum == avgCnt_indx:
        AveragedRows[aRowNum][colNum] = int(AveragedRows[aRowNum][colNum])
      colNum += 1
    aRowNum += 1
  Rows = AveragedRows
  SelectedRowList = []
  iterDict = {}
  rowNum = 0
  for row in Rows:
    SelectedRowList.append(row[iterCol])
    iterDict[row[iterCol]] = rowNum
    rowNum += 1
  return

opString = '+-*/&()'
digitString = '0123456789.'
varString = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
whitespace = ' \t'

opDict = {'+':'NewColAdd',
          '-':'NewColSub',
          '/':'NewColDiv',
          '*':'NewColMult',
          '&':'NewColConcat'
         }

#--- getVarsFromExpr
# Returns a list of variables (names) from the expression (argument)
def getVarsFromExpr(s):
  print >>flog, "getVarsFromExpr:", s
  varNameList = []
  i = 0
  while i < len(s):
    c = s[i]
    if c in opString or c in whitespace or c in digitString:
      i += 1
      continue
    elif c in varString:
      # start of variable name
      varStart =  i
      i += 1
      while i < len(s) and s[i] in varString:
        i += 1
      varNameList.append(s[varStart:i])
  print >>flog, "  varNameList:", varNameList
  return varNameList

#--- getFloat
# reads the floating point number in the string expr that starts at pos
#
def getFloat(expr, pos):
  startPos = pos
  print >>flog, "getFloat, reading floating number in:", expr[pos:]
  while pos < len(expr) and expr[pos] in digitString:
    pos += 1
  num = expr[startPos:pos]
  print >>flog, "  num =", num
  if not isFloat(num):
    doError('newCol, %s is not a floating point number' % num)
  return float(num), pos

#--- getVar
# Gets variable (alpha plus _ characters) in string expr starting at
# pos. It should be a field name, and gets the value of row for that
# field
def getVar(row, expr, pos):
  global fieldDict

  print >>flog, "getVar, reading variable in:", expr[pos:]
  startPos = pos
  while pos < len(expr) and expr[pos] in varString:
    pos += 1
  var = expr[startPos:pos]
  print >>flog, "  varName:", var
  if var not in fieldDict:
    doError('newCol, var "%s" not a known field' % var)
  indx = fieldDict[var]
  if indx >= len(row):
    doError('getVar, indx (%d) of var "%s" too large (%d)' %\
            (indx, var, len(row)))
  val = row[indx]
  print >>flog, "value of var:", var, "=", val
  if isFloat(val):
    return float(val),pos
  else:
    return val,pos

#--- mathRowExpression0
# Evaluate expression where variables refer to field values in given row
#
def mathRowExpression0(row, expr, pos):

  print >>flog, "mathRowExpression0 expr:", expr, " pos:", pos
  n = len(expr)
  stack = []
  num = 0.0
  prevOp = '+'
  while pos < n:
    print >>flog, "  looking at:", expr[pos:]
    c = expr[pos]
    if c in whitespace:
      pos += 1
      continue
    elif c in digitString:
      num,pos = getFloat(expr, pos)
      pos -= 1
      c = 'x'
    elif c in varString:
      num,pos = getVar(row, expr, pos)
      pos -= 1
      c = 'x'
    elif c == '(':
      num,pos = mathRowExpression0(row, expr, pos+1)
      if pos == -1:
        return num, pos
      pos += 1
      continue

    if c == '+' or c == '-'  or c =='*' or c =='/' or c ==')' or c == '&' or \
       pos >= n-1:
      print >>flog, "curOp:", c, " prevOp:", prevOp
      if prevOp == '&':
        stack.append(str(stack.pop()) + str(num))
      else:
        if not isFloat(num):
          return '*', -1
        elif prevOp == '+':
          stack.append(num)
        elif prevOp == '-':
          stack.append(-num)
        elif prevOp == '*':
          prevNum = statck.pop()
          if not isFloat(prevNum) or not isFloat(num):
            return '*', -1
          stack.append(prevNum * num)
        elif prevOp == '/':
          prevNum = stack.pop()
          if not isFloat(prevNum) or not isFloat(num):
            return '*', -1
          if num == 0:
            return '00', -1
          stack.append(prevNum / num)
      prevOp = c
      num = None
    elif c != 'x':
      doError("newCol, error in expression: " + expr)
    pos += 1
    if c == ')':
      break
  rv = 0.0
  while len(stack) > 0:
    v = stack.pop()
    if not isFloat(v) and len(stack) > 0:
      return '*', -1
    rv += v
  return rv,pos-1

#--- mathRowExpression
# Interface for mathRowExpression0
#
def mathRowExpression(row, expr):
  rv,pos = mathRowExpression0(row, expr, 0)
  print >>flog, "mathRowExpression returns:", rv
  return str(rv)

#--- doNewCol1
def doNewCol1(s):
  global AveragedRows
  global AveragedRowsCount
  global fieldDict
  global fieldList
  global SelectedColList
  global SelectedColDict
  global SelectedRowList
  global formatFlag
  global formatList
  global Rows
  global iterDict
  global iterName

  vals = s.split('=', 1)
  newColName = vals[0].strip()
  if len(vals) < 2:
    doError(" newCol missing expression: %s" % s)
  expr = vals[1]
  if newColName in fieldDict:
    doError('Error in "New Column", column name "'+newColName+
            '" already exists.')

  varNameList = getVarsFromExpr(expr)
  for var in varNameList:
    if var not in fieldDict:
      doError('unknown field "%s" in expression "%s" for newCol "%s"' %\
              (var, expr, newColName))

  newColIndx = len(fieldDict)
  fieldDict[newColName] = newColIndx
  fieldList.append(newColName)
  SelectedColList.append(newColName)
  SelectedColDict[newColName] = 1
  if formatFlag:
    if expr.find('/') > 0:
      formatList.append(max(defaultFormat, 2))
    else:
      formatList.append(defaultFormat)

  for r in ReadRowList:
    indx = iterDict[r]
    row = Rows[indx]
    rv = mathRowExpression(row, expr)
    row.append(str(rv))

#--- doNewCol
def doNewCol(newColName):

  global AveragedRows
  global AveragedRowsCount
  global fieldDict
  global fieldList
  global SelectedColList
  global SelectedColDict
  global SelectedRowList
  global formatFlag
  global formatList
  global Rows
  global iterDict
  global iterName

  if newColName in fieldDict:
    doError('Error in "New Column", column name "'+newColName+
            '" already exists.')
  if 'NewColField1' not in CommandDict or CommandDict['NewColField1'] == '':
    doError('Error in "New Column", first field is empty.')
  if 'NewColField2' not in CommandDict or CommandDict['NewColField2'] == '':
    doError('Error in "New Column", second field is empty.')
  field1 = CommandDict['NewColField1']
  field2 = CommandDict['NewColField2']
  if field1 in fieldDict:
    field1Indx = fieldDict[field1]
  elif not isFloat(field1):
    doError('Error in "New Column", field value "'+field1+'" is not a column'
            'name nor a number')
  else:
    field1Float = float(field1)
    field1Indx = -1
  if field2 in fieldDict:
    field2Indx = fieldDict[field2]
  elif not isFloat(field2):
    doError('Error in "New Column", field value "'+field2+'" is not a column'
            'name nor a number')
  else:
    field2Float = float(field2)
    field2Indx = -1
  newColIndx = len(fieldDict)
  fieldDict[newColName] = newColIndx
  fieldList.append(newColName)
  SelectedColList.append(newColName)
  SelectedColDict[newColName] = 1
  op = CommandDict['NewColOp']
  if op in opDict:
    op = opDict[op]
  if formatFlag:
    if op == 'NewColDiv':
      formatList.append(int(2))
    else:
      formatList.append(max(formatList[field1Indx],formatList[field2Indx]))
  for r in ReadRowList:
    indx = iterDict[r]
    row = Rows[indx]
    if field1Indx == -1:
      v1 = field1Float
    elif op == 'NewColConcat':
      v1 = row[field1Indx]
    elif isFloat(row[field1Indx]):
      v1 = float(row[field1Indx])
    else:
      row.append('*')
      continue
    if field2Indx == -1:
      v2 = field2Float
    elif op == 'NewColConcat':
      v2 = row[field2Indx]
    elif isFloat(row[field2Indx]):
      v2 = float(row[field2Indx])
    else:
      row.append('*')
      continue
    if op == 'NewColDiv':
      if v2 != 0:
        v = v1 / v2;
      else:
        row.append('**')
        continue
    elif op == 'NewColMult':
      v = v1 * v2
    elif op == 'NewColAdd':
      v = v1 + v2
    elif op == 'NewColSub':
      v = v1 - v2
    elif op == 'NewColConcat':
      v = '%s_%s' % (v1, v2)
    if (not formatFlag) and (op != 'NewColConcat'):
      v = formatFloat(v)
    if op == 'NewColConcat':
      row.append(v)
    else:
      row.append(str(v))



#--- doSort
def doSort(sortString):

  global CommandDict
  global SelectedRowList
  global fieldDict
  global iterDict
  global Rows
  global SelectedRowList

  sortList = sortString.split(',')
  sortList.reverse()
  print >>flog, 'Inside Sort, col list: ', sortList
  colList = []
  for r in SelectedRowList:
    colList.append(['', r])
  for field in sortList:
    if field[0] == '-':
      sortFun = sortListRevCmp
      field = field[1:]
    else:
      sortFun = sortListCmp
    print >>flog, '  working with field: ', field
    rowList = []
    for e in colList:
      rowList.append(e[1])
    colList = []
    print >>flog, '  current row list: \n', rowList
    if field in fieldDict:
      colIndx = fieldDict[field]
    else:
      print >>flog, '** field ', field, ' not found in fieldDict!'
      doError('Error when trying to sort by. Unknown column name: "'+field+'"')
    for r in rowList:
      indx = iterDict[r]
      row = Rows[indx]
      colList.append([row[colIndx], r])
    print >>flog, '  colList before sort: \n', colList
    colList.sort(sortFun)
    print >>flog, '  colList after sort: \n', colList
  if len(colList) == len(SelectedRowList):
    rowList = []
    for e in colList:
      rowList.append(e[1])
    SelectedRowList = rowList
    print >>flog, '  rowList is the right length, SelectedRowList:\n', \
      SelectedRowList
  return

#--- writeHtmlTable
def writeHtmlTable():
  global CommandDIct, fieldDict, fieldList, formatFlag, formatList
  global showColFormattingFlag, foutPath, foutName, exp
  global SelectedRowList, iterDict, Rows
  global rowColorChangeVal, image

  if 'rowColorChange' in CommandDict:
    rowColorChangeVal = CommandDict['rowColorChange']
    print >>flog, 'rowColorChange in CommandDict, val:', str(rowColorChangeVal)

  if image == ''  and  'Image' in CommandDict and CommandDict['Image'] != '':
    image = CommandDict['Image']
    print >>flog, 'Image in CommandDict:', image, 'using in putHtmlHeader'

  if Mode == 'web':
    sys.stdout.write('Content-type: text/html\n\n')
  if 'Exp' in fieldDict:
    exp = fieldDict['Exp']
  else:
    exp = 'Experiment'
  putHtmlHeader(sys.stdout, fieldList, formatFlag, formatList,
                showColFormattingFlag, foutPath+foutName, exp, image)
  print >>flog, 'Wrote HTML header'
  print >>flog, 'SelectedRowList: ', SelectedRowList
  for r in SelectedRowList:
    indx = iterDict[r]
    putHtmlTableRow(sys.stdout,Rows[indx],fieldList)
  sys.stdout.write('</TABLE></p></FORM>\n')

  if 'PercentTable' in CommandDict:
      percentTableWriteHeader(sys.stdout, fieldList)
      indxTop = iterDict[SelectedRowList[0]]
      for r in SelectedRowList:
        indx = iterDict[r]
        percentTableWriteRow(sys.stdout, fieldList, Rows, indxTop, indx)
      sys.stdout.write('<TABLE></p>\n')

  if Mode == 'web':
    print >>flog, 'image: ', image
    if image != '':
      putImage(image)
  return

#--- doLog
def doLog(fname):
  global flog

  flog.close()
  if fname.lower() == 'null' or fname == '':
    flog = open('/dev/null', 'w')
  else:
    flog = open(fname, 'w')
  return

#--- doPlot0
def doPlot0(fname):
  global CommandDict

  print >>flog, "doPlot0 fname=%s", fname
  CommandDict['plotFilename'] = fname
  image = doPlot()
  print >>flog, "doPlot0 image=%s" % image
  putImage(image)
  return

#--- selectCols
def selectCols(val):
  global SelectedColList, fieldList

  vals = val.split(',')
  if len(vals) == 1 and vals[0] == 'ALL':
    SelectedColList = fieldList*1
    resetSelectedColDict()
  else:
    SelectedColList = []
    for val in vals:
      val = val.strip()
      SelectedColList.append(val)

  resetSelectedColDict()
  return

#--- removeCols
def removeCols(val):
  global fieldDict, SelectedColList

  if len(fieldDict) <= 0:
    return
  vals = val.split(',')
  colList = []
  for val in vals:
    colList.append(val)
  if len(SelectedColList) == 0:
    all_fields = set(fieldDict.keys())
  else:
    all_fields = set(SelectedColList)
  selected_fields = set(colList)
  SelectedColList = list(all_fields - selected_fields)
  resetSelectedColDict()
  return

#--- selectRows
def selectRows(val):
  global iterDict, SelectedRowList

  vals = val.split(',')
  SelectedRowList = []
  for val in vals:
    val = val.strip()
    if val.lower() == 'all':
      SelectedRowList = ReadRowList*1
    elif val in iterDict:
      SelectedRowList.append(val)
    elif val.find('..') > 0:
      n1 = val[0:val.find('..')]
      n2 = val[val.find('..')+2:]
      i = n1
      while i <= n2:
        d = 0
        while True:
          v = str(i) + '.' + str(d)
          if v in iterDict:
            SelectedRowList.append(v)
          else:
            break
          d += 1
        i += 1
  return

#--- doTable
def doTable(val):
  writeHtmlTable()
  return

#--- doSource
# Reads and processes a file of commands
# Variable subsitution is allowed when the filename is followed by a
# list of variable assignments. Input format:
#   <filename>[,var1=val1,var2=val2...]
# Initial blank space of each input line is removed. A line consisting
# of multiple input lines can be formed by using a '\' as the last
# character in an input line that should be appended to a following
# input line.
# Blank space at the end of a whole line is also removed.
#
def doSource(val):
  global flog

  print >>flog, "doSource =", val
  vals = val.split(',')
  if len(vals) <= 0:
    return
  fname = vals[0]
  varDict = {}
  if len(vals) > 1:
    for val in vals[1:]:
       kv = val.split('=', 1)
       if len(kv) != 2:
         doError('in doSource, variable without value:%s' % iline)
       k = kv[0].strip()
       v = kv[1].strip()
       varDict[k] = v
  print >>flog, "doSource varDict:", varDict

  fread = myOpen(fname, 'r')
  useLine = ''
  for iline in fread:
    iline = iline.strip()
    iline = useLine + iline
    if len(iline) == 0 or iline[0] == '#':
      useLine = ''
      continue
    if iline[-1] == '\\':
      useLine = iline[:-1]
      continue
    iline = Template(iline).safe_substitute(varDict)
    iline = iline.strip()
    if len(iline) == 0 or iline[0] == '#':
      continue
    print >>flog, "doSource iline = ", iline
    kv = iline.split('=', 1)
    processCommand(kv)
    useLine = ''
  fread.close()

#--- processCmdDict{}
processCmdDict = {
  'end':doEnd, 'log':doLog, 'read':readCsvFile,
  'append':appendCsvFile, 'select':doSelect, 'average':doAverage,
  'newcol':doNewCol1, 'doplot':doPlot0, 'dotable':doTable,
  'selectcols':selectCols, 'cols':selectCols, 'removecols':removeCols,
  'deletecols':removeCols, 'selectrows':selectRows, 'selectexp':selectRows,
  'rows':selectRows, 'source':doSource
}

#--- processCommand
def processCommand(kv):
  global csvFilename, Rows, flog
  global SelectedRowList, SelectedColList, CommandDict
  global SelectedColDict, fieldDict, fieldList
  global relPath, IterName, Path
  global defaultFormatFlag, defaultFormat

  print >>flog, ">> processCommand: ", kv
  key = kv[0].strip()
  keyLC = key.lower()
  if len(kv) != 2:
    if keyLC == 'doplot' or keyLC == 'dotable' or keyLC == 'end':
      val = None
    else:
     doError("Command:%s is missing its value" % kv[0])
  else:
      val = kv[1].strip()
      if len(val) > 0 and ((val[0] == "'" and val[-1] == "'") or \
         (val[0] == '"' and val[-1] == '"')):
        val = val[1:-1]

  if keyLC == 'end':
    doEnd()

# Commands that can occur before File comamnd:
  if keyLC == 'format':
    if not isFloat(val):
      doError("format argument is not an integer: %s" % val)
    defaultFormatFlag = True
    defaultFormat = int(val)
    return
  elif keyLC == 'log':
    doLog(val)

  if keyLC == 'file' and 'File' not in CommandDict:
    filename = val + '.csv'
    CommandDict['File'] = filename
    relPath = val.rsplit('/',1)[0]
    readCsvFile(filename)
    return

  # File has to be the 1st command, else use default name
  if 'File' not in CommandDict and keyLC != 'log':
    CommandDict['File'] = 'exp'
    readCsvFile('exp')

  if keyLC in processCmdDict:
    print >>flog, 'key %s in processCmdDict' % key
    processCmdDict[keyLC](val)
  elif keyLC == 'path':
    Path = val
  elif keyLC == 'relpath':
    relPath = val
  elif keyLC == 'iterfile':
    IterFile = val
  elif keyLC == 'y1div' and isFloat(val):
    CommandDict[key] = val
  elif keyLC == 'y2div' and isFloat(val):
    CommandDict[key] = val
  elif keyLC == 'plotsize':
    xyval = val.split(',')
    if len(xyval) == 1:
      xyval = val.split('x')
    if len(xyval) >= 2 and isFloat(xyval[1]):
      CommandDict['plotYSize'] = xyval[1]
    if len(xyval) >= 1 and isFloat(xyval[0]):
      CommandDict['plotXSize'] = xyval[0]
  else:
    CommandDict[key] = val
  return

#--- processArgs
def processArgs():

  global SelectedRowList, SelectedColList, CommandDict
  CommandDict['SaveStatic'] = True

  for arg in sys.argv[1:]:
    print >>flog, "arg: ", arg
    kv = arg.split('=', 1)

    if kv[0] == '--file':
      if len(kv) < 2:
        print >> sys.err, "--file argument is missing value"
        doError("--file argument is missing value")
      doSource(kv[1])
    else:
      processCommand(kv)
  doEnd()

#--- processCGIInput
def processCGIInput(fin):
  global csvFilename
  SelectedRowList = []
  SelectedColList = []
  InputLines = []
  CommandDict = {}

  form = cgi.FieldStorage()
  print >>flog, form
  for k in form:
    val = form.getlist(k)
    print >>flog, 'key=',k, 'val=', val
    if k == 'csvFile' and form[k].file:
      fileitem = form[k]
      if fileitem.filename == '':
        continue
      print >>flog, 'We have a non-empy cvsFile!'
      csvFilename = os.path.join(uploadDir,fileitem.filename)
      fout = file(csvFilename, 'w')
      while 1:
        chunk = fileitem.file.read(100000)
        if not chunk: break
        fout.write(chunk)
      fout.close
      continue

    if not isinstance(val,list):
      val = [val]
    for v in val:
      if v == '':
        continue
      if not k in saveIgnoreDict:
        InputLines.append(str(k)+'='+str(v))
      if k == 'Rows':
        SelectedRowList.append(v)
      elif k == 'Cols':
        SelectedColList.append(v)
      else:
        CommandDict[k] = v

  if csvFilename != '' and 'loadCsvFile' in CommandDict:
    if csvFilename[-4:] == '.csv':
      CommandDict['File'] = csvFilename[0:-4]
    else:
      CommandDict['File'] = csvFilename
    CommandDict['IterFile'] = ''
    CommandDict['Path'] = ''


  if 'SaveCommands' in CommandDict:
    fname = CommandDict['SaveCommands']
    if fname != '':
      print >>flog, 'Saving Commands to: ', fname
      fsave = myOpen('Commands/'+ fname, 'w')
      for line in InputLines:
        print >> fsave, line
    if 'BrowseCommands' in CommandDict:
      CommandDict['BrowseCommands'] = ''

  if 'ReadCommands' in CommandDict:
    if 'BrowseCommands' in CommandDict:
      CommandDict['BrowseCommands'] = ''
    fname = CommandDict['ReadCommands']
    if fname != '':
      ReadCommands = 1
      print >>flog, 'Reading Commands from: ', fname
      fread = myOpen('Commands/' + fname, 'r')
      for iline in fread:
        line = iline.strip()
        print >>flog, '    ', iline
        r = line.split('=',1)
        if line.startswith('Rows='):
          SelectedRowList.append(r[1])
        elif line.startswith('Cols='):
          SelectedColList.append(r[1])
        elif r[0] != 'SaveCommands':
          ReadCommandDict[r[0]] = r[1]
      fread.close()

  return SelectedRowList, SelectedColList, CommandDict


#
# --------------  MAIN  ------------------------
#

def to_fn():
  time.sleep(5)
  print >>flog, 'Woke from sleep in to_fn, ending program'
  flog.close()
  os._exit(1)

# --- Main

if Mode == 'web':
  to = threading.Thread(name='to', target=to_fn)
  to.start()

#flog = open('log/log.out', 'w')
if Mode == 'web':
  SelectedRowList, SelectedColList, CommandDict = processCGIInput(sys.stdin)
else:
  SelectedRowList, SelectedColList, CommandDict = processArgs()

print >>flog, 'Selected Row List'
print >>flog, SelectedRowList
print >>flog, '\nSelected Col List'
print >>flog, SelectedColList
print >>flog,'\nCommand Dict'
print >>flog, CommandDict

if 'ReadPage' in CommandDict:
  print >>flog, 'Inside ReadPage'
  sys.stdout.write('Content-type: text/html\n\n')
  sys.stdout.write('<HTML> <HEAD> <TITLE>'+'ReadPage'+'</TITLE>\n')
  sys.stdout.write('</HEAD><BODY><h1>Experiments</h1></BODY>')
  dir_list = os.listdir('Saved')
  for d in dir_list:
    if d.find('html') >= 0:
      sys.stdout.write('<p><A HREF="/Exp/cgi-exec/Saved/'+d+'">'+d+'</A></p>')
  sys.stdout.write('</HTML>')
  print >>flog, 'DONE'
  flog.close()
  sys.stdout.close()
  os._exit(0)

filename = 'blank filename'
if 'File' in CommandDict: filename = CommandDict['File']
filename = filename + '.csv'
print >>flog, 'filename:', filename
#Head, Tail = os.path.split(filename)

if 'Menu' in CommandDict:
  menuState = CommandDict['Menu']
else:
  menuState = ''

if 'Path' in CommandDict:
  Path = CommandDict['Path']
else:
  Path = ''
if 'relPath' in CommandDict:
  relPath = CommandDict['relPath']
else:
  relPath = Path
if 'IterFile' in CommandDict:
  IterFile = CommandDict['IterFile']
else:
  IterFile = ''
print >>flog, 'IterFile: ', IterFile

fieldList, fieldDict, formatFlag, formatList, iterDict, Rows = readCsvFile(filename)
print >>flog, 'Read csv file'
if csvFilename != '' and 'AppendCsvFile' in CommandDict:
  appendCsvFile(csvFilename,fieldList,fieldDict,iterDict,Rows)

if 'CleanDescript' in CommandDict:
  if 'Descript' in fieldDict:
    if 'Ver' in fieldDict:
      descriptIndx = fieldDict['Descript']
      verIndx = fieldDict['Ver']
      for r in Rows:
        descript = r[descriptIndx]
        ver = r[verIndx]
        nver = '-'+ver
        if descript.endswith(ver):
          r[descriptIndx] = descript[:-len(nver)]

if 'Description' in CommandDict and CommandDict['Description'] != '':
  print >>flog, '** MakeDescript called'
  if 'Descript' in fieldDict:
    DescriptionString = CommandDict['Description']
    DescriptionList = DescriptionString.split(",")
    descriptIndx = fieldDict['Descript']
    for r in Rows:
      descript = ''
      for d in DescriptionList:
        if d in fieldDict:
          if d == 'cc' or d == 'ca' or d == 'Notes':
            descript = descript + r[fieldDict[d]] + ' '
          else:
            descript = descript + d + '=' + r[fieldDict[d]] + ' '
      r[descriptIndx] = descript[:-1]
      print >>flog, '  ', descript, ' -> ', r[descriptIndx]

if 'Note' in CommandDict and CommandDict['Note'] != '':
  print >>flog, '** MakeNote called'
  if 'Notes' in fieldDict:
    NoteString = CommandDict['Note']
    NoteList = NoteString.split(",")
    noteIndx = fieldDict['Notes']
    for r in Rows:
      note = ''
      for d in NoteList:
        if d in fieldDict:
          if d == 'cc' or d == 'Notes':
            note = note + r[fieldDict[d]] + ' '
          else:
            note = note + d + '=' + r[fieldDict[d]] + ' '
      r[noteIndx] = note[:-1]
      print >>flog, '  ', note, ' -> ', r[noteIndx]

#if 'AverageBy' in CommandDict and CommandDict['AverageBy'] != '':
#  AverageString = CommandDict['AverageBy']
#  AverageList = AverageString.split(",")

#  AverageColList = []
#  AverageFunList = []

iterIndex = fieldDict[iterName]
for row in Rows:
  ReadRowList.append(row[iterIndex])


SelectAllRowsFlag = False
if 'AllRows' in CommandDict:
  SelectedRowList = ReadRowList
  SelectAllRowsFlag = True

SelectAllColsFlag = False
if 'AllCols' in CommandDict:
  SelectedColList = fieldList
  SelectAllColsFlag = True


if 'DeleteRows' in CommandDict:
  all_iters = set(iterDict.keys())
  selected_iters = set(SelectedRowList)
  SelectedRowList = list(all_iters - selected_iters)
#  SelectedRowList = result.elems
#  SelectedRowList.sort()
  SelectedRowList = sorted(SelectedRowList, cmp=strFloatCmp)

formatDict = {}
for k, v in CommandDict.iteritems():
  if k[0:10] == 'colFormat_':
    newk = k[10:]
    formatDict[newk] = int(v)
if len(formatDict) > 0:
  formatList = []
  for f in fieldList:
    if f in formatDict:
      formatList.append(formatDict[f])
    else:
      formatList.append(0)

SelectedColDict = {}
if 'DeleteCols' in CommandDict:
  all_fields = set(fieldDict.keys())
  selected_fields = set(SelectedColList)
  SelectedColList = list(all_fields - selected_fields)
  for c in SelectedColList:
    SelectedColDict[c] = 1
elif len(SelectedColList) != 0:
  for c in SelectedColList:
    SelectedColDict[c] = 1
else:
  for f in fieldList:
    SelectedColList.append(f)
    SelectedColDict[f] = 1

if not iterName in SelectedColList:
  SelectedColList.append(iterName)
SelectedColDict[iterName] = 1
if not 'Exp' in SelectedColList:
  SelectedColList.append('Exp')
SelectedColDict['Exp'] = 1

if len(SelectedRowList) == 0:
  SelectedRowList = ReadRowList

if 'Select' in CommandDict:
  doSelect(CommandDict['Select'])


if 'AverageBy' in CommandDict and CommandDict['AverageBy'] != '':
  doAverage(CommandDict['AverageBy'])


if 'FilterNotes' in CommandDict and CommandDict['FilterNotes'] != '':
  filter = CommandDict['FilterNotes']
  if 'Notes' in fieldDict:
    notes_index = fieldDict['Notes']
    for r in SelectedRowList:
      indx = iterDict[r]
      row = Rows[indx]
      i = row[notes_index].find(filter)
      if i < 0:
        row[notes_index] = ''
      else:
        row[notes_index] = filter

if 'doRatio' in CommandDict and 'ratio' in fieldDict:
  ratio_indx = fieldDict['ratio']
  if CommandDict['doRatio'] == 'Rate01':
    if 'rate0' in fieldDict and 'rate1' in fieldDict:
      rate0_indx = fieldDict['rate0']
      rate1_indx = fieldDict['rate1']
      for r in SelectedRowList:
        row = Rows[iterDict[r]]
        rate0 = float(row[rate0_indx])
        rate1 = float(row[rate1_indx])
        if rate1 > 0:
          row[ratio_indx] = rate0/rate1
        else:
          row[ratio_indx] = 'inf'
  elif CommandDict['doRatio'] == 'RateMaxMin':
    if 'rate_max' in fieldDict and 'rate_min' in fieldDict:
      rateMax_indx = fieldDict['rate_max']
      rateMin_indx = fieldDict['rate_min']
      for r in SelectedRowList:
        row = Rows[iterDict[r]]
        rateMax = float(row[rateMax_indx])
        rateMin = float(row[rateMin_indx])
        if rateMin > 0:
          row[ratio_indx] = rateMax/rateMin
        else:
          row[ratio_indx] = 'inf'


if 'Sort' in CommandDict:
  doSort(rmSpaces(CommandDict['Sort']))


if 'ScaleColumns' in CommandDict and CommandDict['ScaleColumns'] != '' and 'ScaleFactor' in CommandDict and CommandDict['ScaleFactor'] != '':
  scaleFactor = float(CommandDict['ScaleFactor'])
  print >>flog, '\nScaleFactor: ', scaleFactor
  scaleColumns = CommandDict['ScaleColumns'].split(',')
  print >>flog, '\nScaleColumns'
  print >>flog, scaleColumns
  for r in SelectedRowList:
    indx = iterDict[r]
    row = Rows[indx]
    for f in scaleColumns:
      if f in fieldDict:
        row[fieldDict[f]] = float(row[fieldDict[f]])*scaleFactor

if 'NewColName' in CommandDict:
  newColName = CommandDict['NewColName']
  if newColName in fieldDict:
    doError('Error in "New Column", column name "'+newColName+
            '" already exists.')
  if 'NewColField1' not in CommandDict or CommandDict['NewColField1'] == '':
    doError('Error in "New Column", first field is empty.')
  if 'NewColField2' not in CommandDict or CommandDict['NewColField2'] == '':
    doError('Error in "New Column", second field is empty.')
  field1 = CommandDict['NewColField1']
  field2 = CommandDict['NewColField2']
  if field1 in fieldDict:
    field1Indx = fieldDict[field1]
  elif not isFloat(field1):
    doError('Error in "New Column", field value "'+field1+'" is not a column'
            'name nor a number')
  else:
    field1Float = float(field1)
    field1Indx = -1
  if field2 in fieldDict:
    field2Indx = fieldDict[field2]
  elif not isFloat(field2):
    doError('Error in "New Column", field value "'+field2+'" is not a column'
            'name nor a number')
  else:
    field2Float = float(field2)
    field2Indx = -1
  newColIndx = len(fieldDict) + 1
  fieldDict[newColName] = newColIndx
  fieldList.append(newColName)
  SelectedColList.append(newColName)
  SelectedColDict[newColName] = 1
  op = CommandDict['NewColOp']
  if formatFlag:
    if op == 'NewColDiv':
      formatList.append(int(2))
    else:
      formatList.append(max(formatList[field1Indx],formatList[field2Indx]))
  for r in SelectedRowList:
    indx = iterDict[r]
    row = Rows[indx]
    if field1Indx == -1:
      v1 = field1Float
    elif op == 'NewColConcat':
      v1 = row[field1Indx]
    else:
      v1 = float(row[field1Indx])
    if field2Indx == -1:
      v2 = field2Float
    elif op == 'NewColConcat':
      v2 = row[field2Indx]
    else:
      v2 = float(row[field2Indx])
    if op == 'NewColDiv':
      if v2 != 0:
        v = v1 / v2;
      else:
        v = '/0'
    elif op == 'NewColMult':
      v = v1 * v2
    elif op == 'NewColAdd':
      v = v1 + v2
    elif op == 'NewColSub':
      v = v1 - v2
    elif op == 'NewColConcat':
      v = '%s_%s' % (v1, v2)
    if (not formatFlag) and (op != 'NewColConcat'):
      v = formatFloat(v)
    if op == 'NewColConcat':
      row.append(v)
    else:
      row.append(str(v))

print >>flog, '\nSelected Row List'
print >>flog, SelectedRowList
#print >>flog, '\niterDict'
#print >>flog, iterDict
#print >>flog, '\nAveraged Rows'
#print >>flog, Rows

#--- Do Plot
if 'plotDo' in CommandDict:
  image = doPlot()

print >>flog, 'After Plot'

showColFormattingFlag = False
if 'ShowColFormatting' in CommandDict:
  showColFormattingValue = CommandDict['ShowColFormatting']
  print >>flog, 'COL FORMATTING VALUE: ', showColFormattingValue
  if showColFormattingValue != 'off':
    showColFormattingFlag = True

if 'SavePage' in CommandDict and CommandDict['SavePage'] != '':
  foutPath = 'Saved/'
  foutDir = 'Saved/'
  if not os.path.exists(foutPath):
    os.mkdir(foutPath, 0777)
    os.chmod(foutPath, 0777)

  fileName = CommandDict['SavePage'] + '_' + foutName
  if 'SaveStatic' in CommandDict and CommandDict['SaveStatic']:
    fileName += '_static'
  print >>flog, '\nSavePage foutPath:', foutPath, ' filename:', fileName
  fSave = myOpen(foutPath+fileName+'.html', 'w')
  if 'Image' in CommandDict and CommandDict['Image'] != '':
    imageFile = CommandDict['Image']
    print >>flog, 'Image exists: ', imageFile
    if Mode == 'web':
      shutil.copyfile('/Library/WebServer/Documents/Exp/cgi-exec/'+imageFile, foutPath+foutName+'.jpg')
#    fSave.write('<p><IMG SRC="'+foutPath+foutName+'.jpg'+'"></p>\n')
#    saveImage = foutPath+foutName+'.jpg'
    saveImage = foutName+'.jpg'
  else:
    saveImage = ''
  if 'Exp' in fieldDict:
    exp = fieldDict['Exp']
  else:
    exp = 'Experiments'
  putHtmlHeader(fSave,fieldList,formatFlag,formatList,showColFormattingFlag,foutPath+fileName,exp, saveImage)
  foutName = fileName
  for r in SelectedRowList:
    indx = iterDict[r]
    putHtmlTableRow(fSave,Rows[indx],fieldList)
  fSave.write('</TABLE></p></FORM>\n')
#  if os.path.exists(filename+'.jpg'):
#    print >>flog, 'Image exists: ', filename+'.jpg'
#    shutil.copyfile(filename+'.jpg', foutPath+foutName+'.jpg')
#    fSave.write('<p><IMG SRC="'+foutPath+foutName+'.jpg'+'"></p>\n')

# Write graph if there was a plot
  if image != '':
    print >>flog, 'Write graph if there is a plot:"'+image+'"'
    fout.write('<p><IMG SRC="'+image+' "height="600" width="1200"></p>\n')

  fSave.write('</BODY></HTML>\n')
  fSave.close()

else:

  #--- Do HTML page
  if 'rowColorChange' in CommandDict:
    rowColorChangeVal = CommandDict['rowColorChange']
    print >>flog, 'rowColorChange in CommandDict, val:', str(rowColorChangeVal)

  if image == ''  and  'Image' in CommandDict and CommandDict['Image'] != '':
    image = CommandDict['Image']
    print >>flog, 'Found Image in CommandDict:', image, 'using in putHtmlHeader'

  if Mode == 'web':
    sys.stdout.write('Content-type: text/html\n\n')
  if 'Exp' in fieldDict:
    exp = fieldDict['Exp']
  else:
    exp = 'Experiment'
  putHtmlHeader(sys.stdout,fieldList,formatFlag,formatList,showColFormattingFlag,foutPath+foutName,exp, image)
  print >>flog, 'Wrote HTML header'
  print >>flog, 'SelectedRowList: ', SelectedRowList
  for r in SelectedRowList:
    indx = iterDict[r]
    putHtmlTableRow(sys.stdout,Rows[indx],fieldList)
  sys.stdout.write('</TABLE></p></FORM>\n')
#  if image != '':
#    sys.stdout.write('<p><IMG SRC="'+image+'"></p>\n')

  if 'PercentTable' in CommandDict:
      percentTableWriteHeader(sys.stdout, fieldList)
      indxTop = iterDict[SelectedRowList[0]]
      for r in SelectedRowList:
        indx = iterDict[r]
        percentTableWriteRow(sys.stdout, fieldList, Rows, indxTop, indx)
      sys.stdout.write('<TABLE></p>\n')

  print >>flog, 'image: ', image
  if image != '':
    putImage(image)

  endHtml()
  print >>flog, 'Wrote HTML Rows'

#--- Write csv file
if Mode == 'web':
  fout = myOpen(foutPath+foutName+'.csv', 'w')
  count = 0
  indx = 0
  if Path != '':
    fout.write('#Path:'+Path+'\n')
  for f in fieldList:
    if f in SelectedColList and SelectedColDict[f] == 1:
      if formatFlag:
        f = f+':'+str(formatList[indx])
      if count == 0:
        fout.write(f)
      else:
        fout.write(','+f)
      count += 1
    indx += 1
  fout.write('\n')
  print >>flog, 'Wrote csv header'

  for r in SelectedRowList:
    indx = iterDict[r]
    row = Rows[indx]
    count = 0
    fieldIndex = 0
    for item in row:
      f = fieldList[fieldIndex]
      fieldIndex += 1
      if f in SelectedColList and SelectedColDict[f] == 1:
        if count == 0:
          fout.write(item)
        else:
          fout.write(','+str(item))
        count += 1
    fout.write('\n')
  print >>flog, 'Wrote csv rows'
  fout.close()
  os.chmod(foutPath+foutName+'.csv',0666)

if 'SavePage' in CommandDict and CommandDict['SavePage'] != '':
  print >>flog, 'Inside last SavePage'
  sys.stdout.write('Content-type: text/html\n\n')
  sys.stdout.write('<HTML> <HEAD> <TITLE>'+'TEST'+'</TITLE>\n')
#  sys.stdout.write('<meta HTTP-EQUIV="REFRESH" content="0; url=http://'+hostName+'/tmp/'+foutDir+foutName+'.html">')
  sys.stdout.write('<meta HTTP-EQUIV="REFRESH" content="0; url=http://localhost/Exp/cgi-exec/'+foutDir+foutName+'.html">')
  sys.stdout.write('</HEAD><BODY>Redirection to saved page</BODY>')
  sys.stdout.write('</HTML>')


print >>flog, 'DONE'
flog.close()
sys.stdout.close()
os._exit(0)
#sys.stdout.close()
