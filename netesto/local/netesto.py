#!/usr/local/bin/python

# netesto.py - program to run distributed network experiments
#
# Copyright (C) 2016, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the LICENSE
# file in the root directory of this source tree.

import sys, random, os, os.path, commands, getopt
import socket
import subprocess
import struct
import select
import time

ERROR = -1

MSG_HEADER_FORMAT="!ii"
MSG_HEADER_LEN=0

#
# Remote commands require a new message
# Message related variables. Messages are between controller and clients/severs
#
MSG_DO_SERVER = 0
MSG_DO_CLIENT = 1
MSG_GET_DATA = 2
MSG_RETURN_VALUE = 3
MSG_FILE = 4
MSG_CLOSE = 5
MSG_EXIT = 6
MSG_SET_MODULE_PARAMS = 7
MSG_SET_SYSCTL = 8
MSG_SET_NETEM = 9
MSG_TCPDUMP = 10
MSG_SET_QDISC = 11
MSG_MAX = 11

MSG_FORMAT = [
    "!ihh",                                     # MSG_DO_SERVER
    "!i 100s 20s 3i 20s 20s 3i 20s i 40s",      # MSG_DO_CLIENT
    "!i",                                       # MSG_GET_DATA
    "",                                         # MSG_RETURN_VALUE
    "!100s i",                                  # MSG_FILE
    "",                                         # MSG_CLOSE
    "",                                         # MSG_EXIT
    "!30s 200s",                                # MSG_SET_MODULE_PARAMS
    "!400s",                                    # MSG_SET_SYSCTL
    "!i i s",                                   # MSG_SET_NETEM
    "!i i 100s",                                # MSG_TCPDUMP
    "!20s 20s 20s 20s 20s"                      # MSG_SET_QDISC
]

MSG_LEN = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
MSG_NAME = ["MSG_DO_SERVER", "MSG_DO_CLIENT", "MSG_GET_DATA",
            "MSG_RETURN_VALUE", "MSG_FILE", "MSG_CLOSE", "MSG_EXIT",
            "MSG_SET_MODULE_PARAMS", "MSG_SET_SYSCTL", "MSG_SET_NETEM",
            "MSG_TCPDUMP", "MSG_SET_QDISC", "MSG_ERROR"
]

setModParamDict = { \
    "tcp_nv" :
    ["nv_max_rtt_us", "nv_set_dscp", "nv_geo_mask",
    "nv_cluster_max_rtt", "nv_dc_max_rtt", "nv_mero_max_rtt",
     "nv_enable", "nv_pad", "nv_pad_buffer", "nv_test",
    "nv_min_cwnd", "nv_max_min_rtt", "nv_min_min_rtt_percent",
    "nv_reset_period", "nv_cong_decrease_mul", "nv_cwnd_growth_factor",
    "nv_dec_eval_min_calls", "nv_dec_factor", "nv_loss_dec_factor",
    "nv_rtt_cnt_dec_delta", "nv_rtt_factor", "nv_rtt_min_cnt",
    "nv_ssthresh_eval_min_calls", "nv_ssthresh_factor"
    ],
    "tcp_dctcp" :
    ["dctcp_max_rtt_us", "dctcp_geo_mask"
    ]
}

setSysctlDict = { \
    "net.core.rmem_max" : [[2621440, 67108864]],
    "net.core.wmem_max" : [[2621440, 67108864]],
    "net.ipv4.tcp_wmem" : [[4096, 10000], [16000, 270000], [128000, 61000000]],
    "net.ipv4.tcp_rmem" : [[4096, 10000], [16000, 270000], [128000, 61000000]],
    "net.ipv4.tcp_allowed_congestion_control" : None,
    "net.ipv4.tcp_cong_dscp_mask" : [[0, 255]],
    "net.ipv4.tcp_cong_dscp_val"  : [[0, 255]],
    "net.ipv4.tcp_ecn" : [[0, 2]],
    "net.ipv4.tcp_congestion_control" : None,
    "net.ipv4.tcp_min_rto_ms": [[20, 200]]
}

TEST_FILE="This is the test file, only one line"

#flog = open('netesto.log', 'w')

SERVER_PORT = 31840
MAX_PORTS = 5
serverPort = SERVER_PORT

HostName = 'unknown'
serverSocket = None
serverFlag = False
#hostname to socket dictionary
hostDict = {}
# list of allowed client ipv6 addresses from clients.txt
clientDict = {}
socketDict = {}
socketBufferDict = {}
readList = []
rcvBuf = ''
lastHost = ''
lastGroup = 1
lastExp = ''
lastExpName = ''
debugFlag = False
debugFlagSaved = False
debugOutput = sys.stdout
noRunFlag = False
defaultHostSuffix = "mynetwork.com"
getDataHostDict = {}
varDict = {}
descStr = None
otherStr = ""
forDict = None
forStack = []
forLoopList = []
forCount = 0
forDefFlag = False
forLoopPrint = False

# Function definition and processing
funDict = {}		# function name to line list mapping
funLineList = None	# Contains list of lines in function during definition
funName = None		# Name of function being defined

#--- init
def init():
    k = 0
    for f in MSG_FORMAT:
        MSG_LEN[k] = struct.calcsize(f)
        k += 1
    MSG_HEADER_LEN=struct.calcsize(MSG_HEADER_FORMAT)

#--- doDebug
def doDebug(s):
    if debugFlag:
        debugOutput.write("%s\n" % s)

#--- flushDebug
def flushDebug():
    if debugFlag == True and debugOutput != sys.stdout:
        debugOutput.flush()
        os.fsync(debugOutput.fileno())

#--- exit
def exit(v):
    global serverSocket

    doDebug("Calling sys.exit(%d)\n" % v)
    if serverSocket != None:
        serverSocket.close()
    sys.exit(v)

#--- error
def error(msg):
    print "ERROR: "+msg
    exit(2)

#--- printUsage
def printUsage():
    print "Usage:", sys.argv[0], "[-s] [-d|--debug=<filename>] [--port=<serverPort>]"

#--- cleanStr
def cleanStr(s):
    ns = ''
    for c in s:
        if ord(c)  >= 32:
            ns += c
        elif ord(c) != 0:
            doDebug("cleanStr found a suspicious character:%d" % ord(c))
    return ns

#--- getValue
def getValue(val, funArgDict, statement, errFlag=True):
    if val[0] == '$':
        if funArgDict is not None and val[1:] in funArgDict:
            return funArgDict[val[1:]]
        elif val[1:] not in varDict:
            if errFlag:
                error("Undefined variable '%s' in %s" % (val, statement))
            else:
                return val
        return varDict[val[1:]]
    return val

#--- sockName
def sockName(sock):
    if id(sock) in socketDict:
        return socketDict[id(sock)]
    else:
        return 'NOT FOUND'

#--- closeClientSocket
def closeClientSocket(sock, closeFlag):
    global socketDict, hostDict

    doDebug("closing client socket " + sockName(sock))
    hostDict[socketDict[id(sock)]] = None
    socketDict[id(sock)] = 'CLOSED'
    socketBufferDict[id(sock)] = ''
    if closeFlag:
        sock.close()

#--- closeAServerSocket
def closeAServerSocket(sock, closeFlag):
    global socketDict, readList

    doDebug("closing server socket " + sockName(sock))
    readList.remove(sock)
    socketDict[id(sock)] = "CLOSED"
    socketBufferDict[id(sock)] = ''
    flushDebug()
    if closeFlag:
        sock.close()

#--- runCmd
def runCmd(cmdStr, outFilename=None):
    global noRunFlag

    doDebug("runCmd: " + cmdStr + " outFile:" + str(outFilename))
    if noRunFlag:
        doDebug("-- Skipping beause of noRunFlag")
        return
    args = cmdStr.split()
    #subprocess.call(args)
    if outFilename == None:
        subprocess.Popen(args, ).pid
    else:
        outFile = open(outFilename, 'w')
        subprocess.Popen(args, stdout=outFile).pid

#--- read
def read(sock, n):
    global socketBufferDict

    if not id(sock) in socketBufferDict:
        doDebug("cannot read from " + sockName(sock) + ", not in bufferDict")
        return ''

    rcvBuf = socketBufferDict[id(sock)]
    while len(rcvBuf) < n:
        try: s = sock.recv(2048)
        except (socket.error), e: return ''
        if len(s) == 0:
            doDebug("NON-FATAL ERROR: read returns 0 for "+sockName(sock))
            return ''
        doDebug("read %d bytes on socket %s" % (len(s), sockName(sock)))
        rcvBuf += s
    s = rcvBuf[:n]
    socketBufferDict[id(sock)] = rcvBuf[n:]
    return s

#--- processExp
def processExp(subdir):
    global descStr
    global otherStr

    if not os.path.isdir(subdir):
        return

    files = os.listdir(subdir)
    monitorList = []
    netperfList = []
    for file in files:
        if file.find('monitor') >= 0:
            monitorList.append(subdir + '/' + file)
        elif file.find('ss') >= 0 and file.find('.out') >= 0:
            monitorList.append(subdir + '/' + file)
        elif file.find('netperf') >= 0:
            netperfList.append(subdir + '/' + file)
    doDebug("monitorList: " + str(monitorList))
#	doDebug("netperfList: " + str(netperfList))

    cmd = ["./plotMonitor.py", "send"]
    cmd.extend(monitorList)
    doDebug("Calling: " + str(cmd))
    subprocess.call(cmd)
    cmd = ["./plotMonitor.py", "cwnd"]
    cmd.extend(monitorList)
    doDebug("Calling: " + str(cmd))
    subprocess.call(cmd)
    cmd = ["./plotMonitor.py", "rtt"]
    cmd.extend(monitorList)
    doDebug("Calling: " + str(cmd))
    subprocess.call(cmd)

    cmd = ["egrep",  "-c", "vegas_minrtt"]
    cmd.extend(monitorList)
    fout = open('x.tmp', 'w')
    subprocess.call(cmd, stdout=fout)
    fout.close()
    fin = open('x.tmp', 'r')
    for line in fin:
        line = line.strip()
        if line[0] != '0':
            cmd = ["./plotMonitor.py", "vegas_minrtt"]
            cmd.extend(monitorList)
            doDebug("Calling: " + str(cmd))
            subprocess.call(cmd)
        break
    cmd = ["./plotNetperfRates.py"]
    cmd.extend(netperfList)
    doDebug("Calling: " + str(cmd))
    subprocess.call(cmd)
    cmd = ["./makeResultsPage.py", subdir]
    doDebug("Calling: " + str(cmd))
    subprocess.call(cmd)

    if not os.path.isfile('exp.csv'):
        p = os.getcwd()
        d = p[p.rfind('/'):]
        cmd = ["./processExp.py",
                "-c",
                "--path=/Library/webServer/Documents/Exp" + d,
                "--relPath=/Exp" + d]
        doDebug("Calling: " + str(cmd))
        subprocess.call(cmd)

    n = 0
    tx_packets_sum = 0
    retrans_packets_sum = 0
    fout = open(subdir + '/all.exp.out', 'w')
    for file in files:
        if file.find('.exp.out') < 0:
            continue
        n += 1
        fname = subdir + '/' + file
        fin = open(fname, 'r')
        for line in fin:
            line = line.strip()
            kv = line.split(':')
            if len(kv) >= 2:
                k, v = kv
                if k == 'exp':
                    v = v[:v.find('.')] + '.0'
                elif k == 'client-tx-packets':
                     tx_packets_sum += float(v)
                elif k == 'retrans_total':
                     retrans_packets_sum += float(v)
                fout.write("%s:%s\n" % (k, v))
        fin.close()

    tx_packets_sum += 1
    retransPktsPercent = 100.0 * retrans_packets_sum / tx_packets_sum
    fout.write("retransPkts%%:%.2f\n" % (retransPktsPercent))
    fout.write("-----\n")
    fout.close()
    if n >= 1:
        fname = subdir + '/all.exp.out'
        if descStr == None:
            cmd = ["./processExp.py", "-a", "--rfile="+fname, "--other="+otherStr]
        else:
            cmd = ["./processExp.py", "-a", "--rfile="+fname,
                   "--desc="+descStr, "--other="+otherStr]
        doDebug("Calling: " + str(cmd))
        subprocess.call(cmd)

    if n == 1:
        return

    for file in files:
        if file.find('.exp.out') > 0:
            fname = subdir + '/' + file
            if descStr == None:
                cmd = ["./processExp.py", "-a", "--rfile="+fname,
                        "--other="+otherStr]
            else:
                cmd = ["./processExp.py", "-a", "--rfile="+fname,
                       "--desc="+descStr, "--other="+otherStr]
            doDebug("Calling: " + str(cmd))
            subprocess.call(cmd)

#--- readFile
def readFile(sock, filename, size):
    f = open("in_" + filename, "wb")
    left = size
    while left > 0:
        b = read(sock, min(4096, left))
        if b == '':
            return ERROR
        f.write(b)
        left -= len(b)
    if left > 0:
        doDebug("Warning: readFile %s only read %d bytes of %d"
            % (filename, size-left, size))
    f.close()
    if filename.find('tgz') > 0:
        cmd = ["tar", "-zxf", "in_" + filename]
        doDebug("Calling: " + str(cmd))
        subprocess.call(cmd)
        cmd = ["rm", "-f", "in_" + filename]
        doDebug("Calling: " + str(cmd))
        subprocess.call(cmd)

#--- rcvMsg
def rcvMsg(sock):
    doDebug("rcvMsg sock:" + str(sockName(sock)))
    s = read(sock, 8)
    if len(s) == 0:
        doDebug("read fails for " + sockName(sock))
        return ERROR, 0
    msgType, msgLen = struct.unpack(MSG_HEADER_FORMAT, s)
    if msgType > MSG_MAX:
        doDebug("msgType > MSG_MAX (%d)" % msgType)
        return ERROR, 0
    doDebug("msgType:%s, msglen:%d" % (MSG_NAME[msgType], msgLen))

    if msgType == MSG_RETURN_VALUE or msgLen == 0:
        return msgType, msgLen
    else:
        s = read(sock, MSG_LEN[msgType])
        if len(s) == 0:
            return ERROR, 0
        msgData = struct.unpack(MSG_FORMAT[msgType], s)
        return msgType, msgData

#--- send
def send(sock, s):
    total = len(s)
    doDebug("sending %d bytes on socket %s" % (total,sockName(sock)))
    count = 0
    while count < total:
        try: n = sock.send(s)
        except (socket.error), e: n = 0
        doDebug("  sent %d bytes" % n)
        if n == 0:
            return 0
        count += n
    return count

#--- createMsgHdr
def createMsgHdr(sock, msgType, msgLen):
    s = struct.pack(MSG_HEADER_FORMAT, msgType, msgLen)
    #send(sock, s)
    return s

#--- sendMsgDoServer
def sendMsgDoServer(sock, argDict):

    doDebug("sendMsgDoServer exp:%s order:%s start:%s" \
            % (argDict["exp"], argDict["order"], argDict["start"]))
    s = createMsgHdr(sock, MSG_DO_SERVER, MSG_LEN[MSG_DO_SERVER])
    s += struct.pack(MSG_FORMAT[MSG_DO_SERVER], int(argDict["exp"]),
            int(argDict["order"]), int(argDict["start"]))
    return send(sock, s)

#--- sendMsgDoClient
def sendMsgDoClient(sock, argDict):
    global lastGroup
    global defaulHostSuffix

    if int(argDict["group"]) == 0:
        argDict["group"] = lastGroup
        lastGroup += 1

    if not "server" in argDict:
        doDebug("server argument missing in DO_CLIENT command")
        error("server argument missing in DO_CLIENT command")

    # Add default DC to server if necessary
    server = argDict["server"]
    if server.find(".") < 0:
        server += "." + defaultHostSuffix

    doDebug("sndMsgDoClient exp=%s server=%s ca=%s dur=%s delay=%s instances:%s test=%s expName=%s" \
            % (argDict["exp"], server, argDict["ca"], argDict["dur"], \
               argDict["delay"], argDict["instances"], argDict["test"], \
               argDict["expName"]))
    s = createMsgHdr(sock, MSG_DO_CLIENT, MSG_LEN[MSG_DO_CLIENT])
    s += struct.pack(MSG_FORMAT[MSG_DO_CLIENT], int(argDict["exp"]),
            server, argDict["ca"], int(argDict["dur"]),
            int(argDict["delay"]), int(argDict["instances"]),
            argDict["req"], argDict["reply"], int(argDict["stats"]),
            int(argDict["localBuffer"]), int(argDict["remoteBuffer"]),
            argDict["test"], int(argDict["group"]), argDict["expName"])
    return send(sock, s)

#--- sendMsgGetData
def sendMsgGetData(sock, argDict):
    s = createMsgHdr(sock, MSG_GET_DATA, MSG_LEN[MSG_GET_DATA])
    s += struct.pack(MSG_FORMAT[MSG_GET_DATA], int(argDict["exp"]))
    return send(sock, s)

#--- sendMsgRV
def sendMsgRV(sock, rv):
    s = createMsgHdr(sock, MSG_RETURN_VALUE, rv)
    return send(sock, s)

#--- sendMsgClose
def sendMsgClose(sock, argDict):
    s = createMsgHdr(sock, MSG_CLOSE, 0)
    send(sock, s)
    closeClientSocket(sock, True)
    return 1

#--- sendMsgExit
def sendMsgExit(sock, argDict):
    s = createMsgHdr(sock, MSG_EXIT, 0)
    return send(sock, s)

#--- sendMsgSetModuleParams
def sendMsgSetModuleParams(sock, argDict):
    s = createMsgHdr(sock, MSG_SET_MODULE_PARAMS,
            MSG_LEN[MSG_SET_MODULE_PARAMS])
    if 'module' not in argDict:
        error('SET_MODULE_PARAMS: missing "module" argument')
    module = argDict['module']
    modParams = ''
    if module not in setModParamDict:
        error('SET_MODULE_PARAMS: unknow module:%s' % module)
    for p in setModParamDict[module]:
        if p in argDict:
            if len(modParams) == 0:
                modParams += "%s=%s" % (p, argDict[p])
            else:
                modParams += ",%s=%s" % (p, argDict[p])
    s += struct.pack(MSG_FORMAT[MSG_SET_MODULE_PARAMS], module, modParams)
    return send(sock, s)

#--- sendMsgSetSysctl
def sendMsgSetSysctl(sock, argDict):
    msg = createMsgHdr(sock, MSG_SET_SYSCTL,
            MSG_LEN[MSG_SET_SYSCTL])
    sysctls = ''
    for s in setSysctlDict:
        if s in argDict:
            vals = argDict[s].split(',')
            valRanges = setSysctlDict[s]
            if valRanges is not None and len(vals) != len(valRanges):
                error('SET_SYSCTL %s: expecting %d values but only got %d' % \
                        (s, len(valRanges), len(vals)))
            i = 0
            for v in vals:
                if valRanges is not None and (int(v) < valRanges[i][0] \
                        or int(v) > valRanges[i][1]):
                    error('SET_SYSCTL %s: %s  out of range (%d:%d)' %\
                            (s, v, valRanges[i][0], valRanges[i][1]))
                if i == 0 and len(sysctls) == 0:
                    sysctls += "%s=%s" % (s, v)
                elif i == 0:
                    sysctls += " %s=%s" % (s, v)
                else:
                    sysctls += ",%s" % v
                i += 1
    doDebug("SET_SYSCTL: sysctls = %s" % sysctls)
    if len(sysctls) > 0:
        msg += struct.pack(MSG_FORMAT[MSG_SET_SYSCTL], sysctls)
    return send(sock, msg)

#--- sendMsgSetNetem
def sendMsgSetNetem(sock, argDict):
    s = createMsgHdr(sock, MSG_SET_NETEM, MSG_LEN[MSG_SET_NETEM])
    if 'limit' in argDict:
        limit = int(argDict['limit'])
    else:
        limit = 1000
    if 'loss' in argDict:
        loss = argDict['loss']
    else:
        loss = '0.0'
    s += struct.pack(MSG_FORMAT[MSG_SET_NETEM], int(argDict["netem_delay"]),
            limit, loss)
    return send(sock, s)

#--- sendMsgTcpDump
def sendMsgTcpDump(sock, argDict):
    s = createMsgHdr(sock, MSG_TCPDUMP, MSG_LEN[MSG_TCPDUMP])
    s += struct.pack(MSG_FORMAT[MSG_TCPDUMP], int(argDict["exp"]),
                     int(argDict["packets"]), argDict["server"])
    return send(sock, s)

#--- getOptArg(argDict, arg, optValue, where)
def getOptArg(argDict, arg, optValue, where):
    if arg in argDict:
        return argDict[arg]
    elif optValue != None:
        return optValue
    else:
        error("Required argument %s missing in %s" % (arg, where))

#--- sendMsgSetQdisc
def sendMsgSetQdisc(sock, argDict):
    s = createMsgHdr(sock, MSG_SET_QDISC, MSG_LEN[MSG_SET_QDISC])
    s += struct.pack(MSG_FORMAT[MSG_SET_QDISC],
            getOptArg(argDict, "qdisc", None, "SET_QDISC"),
            getOptArg(argDict, "rate", "", "SET_QDISC"),
            getOptArg(argDict, "burst", "", "SET_QDISC"),
            getOptArg(argDict, "limit", "", "SET_QDISC"),
            getOptArg(argDict, "other", "", "SET_QDISC"))
    return send(sock, s)

#
# Remote commands
#
CMD_DICT = {"DO_SERVER":sendMsgDoServer, "DO_CLIENT":sendMsgDoClient,
    "GET_DATA":sendMsgGetData, "CLOSE":sendMsgClose, "EXIT":sendMsgExit,
    "SET_MODULE_PARAMS":sendMsgSetModuleParams,
            "SET_SYSCTL":sendMsgSetSysctl, "SET_NETEM":sendMsgSetNetem,
            "DO_TCPDUMP":sendMsgTcpDump, "SET_QDISC":sendMsgSetQdisc}


#--- sendFile
def sendFile(sock, name, size):
    f = open(name, "rb")
    b = f.read(4096)
    sent = 0
    while b:
        n = send(sock, b)
        if n == 0:
            return ERROR
        else:
            sent += n
            b = f.read(4096)
    f.close()
    if size != sent:
        doDebug("Warning in sendFile(%s), size(%d) != sent(%d)"
                % (name, size, sent))
    else:
        doDebug("sendFile(%s, %s, %d) succeeds" % (sockName(sock), name, size))
    return sent

#--- sendMsgFile
def sendMsgFile(sock, filename):
    try:
        size = os.path.getsize(filename)
    except IOError as  e:
        doDebug(str(e))
        return ERROR
    s = createMsgHdr(sock, MSG_FILE, MSG_LEN[MSG_FILE])
    s += struct.pack(MSG_FORMAT[MSG_FILE], filename, size)
    if send(sock, s) <= 0:
        return ERROR
    sentSize = sendFile(sock, filename, size)
    if sentSize == size:
        return sentSize
    else:
        return ERROR

#--- doRandomWait(t0, t1):
def doRandomWait(t0, t1):
    if t0 == t1:
        time.sleep(t0)
    else:
        d = t1 - t0
        r = random.random() * d
        time.sleep(t0 + r)

#--- doWait
def doWait(t):
    time.sleep(t)

#--- getSocket
def getSocket(host):
    global hostDict
    global socketDict
    global socketBufferDict

    doDebug("getSocket, looking for:" + host)
    if (not host in hostDict) or hostDict[host] == None:
        doDebug("  not in hostDict, creating new one")
        sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            sock.connect((host, serverPort))
        except socket.error as e:
            doDebug("ERROR in getSocket(%s): %s" % (host, str(e)))
            return None
        hostDict[host] = sock
        socketDict[id(sock)] = host
        socketBufferDict[id(sock)] = ''
        doDebug("  new socket: " + sockName(sock))
        return sock
    else:
        doDebug("  found it!")
        return hostDict[host]

#--- processMsg
def processMsg(sock, msgType, msgData):
    global noRunFlag
    global HostName

    doDebug("Processing: " + MSG_NAME[msgType] + " " + str(msgData))
    if msgType == MSG_CLOSE:
        sock.close()
        readList.remove(sock)
        return 1
    elif msgType == MSG_EXIT:
        sendMsgRV(sock, 1)
        sock.close()
        exit(0)
    elif msgType == MSG_DO_SERVER:
        exp, order, start = msgData
        doDebug("MSG_DO_SERVER exp:%d, order:%d, start:%d"
            % (exp, order, start))
        cmdStr = ("./doServer.sh --exp=%d --order=%d --start=%d"
            % (exp, order, start))
        runCmd(cmdStr, "/dev/null")
    elif msgType == MSG_DO_CLIENT:
        exp, server, ca, dur, delay, instances, req, reply, stats, \
            localBuffer, remoteBuffer, test, group, expName = msgData
        doDebug("MSG_DO_CLIENT exp:%d, server:%s, ca:%s"
            % (exp, server, ca))
        server = cleanStr(server)
        ca = cleanStr(ca)
        req = cleanStr(req)
        reply = cleanStr(reply)
        test = cleanStr(test)
        expName = cleanStr(expName)

        cmdStr = (("./doClient.sh --exp=%d --server=%s --ca=%s --dur=%d "
            + "--delay=%d --instances=%d --req=%s --reply=%s --stats=%d "
            + "--local_buffer=%d --remote_buffer=%d --test=%s --group=%d "
            + "--name=%s")
            % (exp, server, ca, dur, delay, instances, req, reply, stats,
               localBuffer, remoteBuffer, test, group, expName))
        runCmd(cmdStr, "/dev/null")
    elif msgType == MSG_GET_DATA:
        exp = msgData[0]
        doDebug("MSG_GET_DATA exp:%d" % exp)
        tarFilename = "%d.tgz" % exp
        if noRunFlag:
            return sendMsgRV(sock, 1)
        else:
            cmd = ["tar", "-zcf", tarFilename, "%d" % exp]
            subprocess.call(cmd)
            rv = sendMsgFile(sock, tarFilename)
            if rv != ERROR:
                cmd = ["rm", "-fR", tarFilename, str(exp)]
                subprocess.call(cmd)
        return 1
    elif msgType == MSG_SET_MODULE_PARAMS:
        module, paramStr = msgData
        module = cleanStr(module)
        paramStr = cleanStr(paramStr)
        doDebug("MSG_SET_MODULE_PARAMS: %s %s" % (module, paramStr))
        paramList = paramStr.split(',')
        for param in paramList:
            kv = param.split('=')
            p,v = kv

            cmd = ["./setParam.sh", module, p, v]
            subprocess.call(cmd)
    elif msgType == MSG_SET_SYSCTL:
        if len(msgData) != 1:
            doDebug("SET_SYSCTL: msgData has len:%d" % len(msgData))
            flushDebug()
        sysctlStr = cleanStr(msgData[0])
        sysctlStr = sysctlStr.strip()
        doDebug("MSG_SET_SYSCTL: %s" % sysctlStr)
        sysctlList = sysctlStr.split(' ')
        for sysctl in sysctlList:
            kv = sysctl.split('=')
            s,vals = kv
            if len(kv) != 2:
                doDebug("SET_SYSCTL: len(kv) = %d != 2!" % len(kv))
                flushDebug()
                sendMsgRV(sock, 0)
                return 1
            if s not in setSysctlDict:
                doDebug("SET_SYSCTL: Unknown sysctl %s" % s)
                sendMsgRV(sock, 0)
                return 1
            vals = vals.split(',')
            valRanges =  setSysctlDict[s]
            if valRanges is not None and len(valRanges) != len(vals):
                doDebug("SET_SYSCTL %s: Number of values does not match" % s)
                sendMsgRV(sock, 0)
                return 1
            sysctlStr = ''
            i = 0
            for v in vals:
                if valRanges is not None and (int(v) < valRanges[i][0] \
                        or int(v) > valRanges[i][1]):
                    doDebug('SET_SYSCTL %s: %s  out of range (%d:%d)' %\
                            (s, v, valRanges[i][0], valRanges[i][1]))
                if len(sysctlStr) == 0:
                    sysctlName = s
                    sysctlStr = v
                else:
                    sysctlStr += ' %s' % v
                i += 1

            cmd = ["./setSysctl.sh", sysctlName, sysctlStr]
            doDebug('SET_SYSCTL: Callying sysctl -w %s="%s"' % \
                    (sysctlName, sysctlStr))
            subprocess.call(cmd)
    elif msgType == MSG_SET_NETEM:
        delay = msgData[0]
        limit = msgData[1]
        loss = msgData[2]
        loss = cleanStr(loss)
        doDebug("MSG_SET_NETEM delay:%d, limit:%d, loss:%s" % (delay,
            limit, loss))
        if noRunFlag:
            return sendMsgRV(sock, 1)
        else:
            cmd = ["tc",  "qdisc", "del", "dev", "eth0", "root"]
            subprocess.call(cmd)
            if delay > 0:
                cmd = ["tc", "qdisc", "add", "dev", "eth0", "root", "netem",\
                       "delay", "%dms" % delay, "limit", "%d" % limit,
                       "loss", "%s%%" % loss]
                subprocess.call(cmd)
    elif msgType == MSG_TCPDUMP:
        exp, packets, server = msgData
        server = cleanStr(server)
        doDebug("MSG_TCPDUMP exp:%d pkts:%d server:%s" % (exp, packets,
                                                          server))
        if noRunFlag:
            return sendMsgRV(sock, 1)
        else:
            cmd = ["tcpdump", "-K", "-s", "96", "-w",
                   str(exp)+'/'+HostName+'-'+server+'.pcap',
                   "-c", str(packets), "-i", "eth0", "host", server]
            doDebug("cmd: %s" % str(cmd))
            os.mkdir(str(exp))
            subprocess.Popen(cmd)
    elif msgType == MSG_SET_QDISC:
        qdisc, rate, burst, limit, other = msgData
        qdisc = cleanStr(qdisc)
        rate = cleanStr(rate)
        burst = cleanStr(burst)
        limit = cleanStr(limit)
        other = cleanStr(other)
        doDebug("MSG_SEQ_QDISC qdisc:%s rate:%s burst:%s limit:%s other:%s" %\
                (qdisc, rate, burst, limit, other))
        if noRunFlag:
            return sendMsgRV(sock, 1)
        else:
            cmd = ["tc", "qdisc", "del", "root", "dev", "eth0"]
            subprocess.call(cmd)
            cmd = ["tc", "qdisc", "add", "dev", "eth0", "root", qdisc]
            if rate != '':
                cmd.append("rate")
                cmd.append(rate)
            if burst != '':
                cmd.append("burst")
                cmd.append(burst)
            if limit != '':
                cmd.append("limit")
                cmd.append(limit)
            if other != '':
                others = other.split()
                for o in others:
                    cmd.append(o)
            doDebug("cmd: %s" % str(cmd))
            subprocess.call(cmd)

    else:
        doDebug("  Unknown message")
        sendMsgRV(sock, 0)
        return 0

    return sendMsgRV(sock, 1)

#--- getArg(arg, funArgDict, where)
def getArg(arg, funArgDict, where):
    global varDict

    if funArgDict != None and arg[0] == "$" and (arg[1:] in funArgDict):
        t = funArgDict[arg[1:]]
        doDebug("%s  from fun argument: %s" % (where, t))
    else:
        t = arg
        if t[0] == "$":
            if not t[1:] in varDict:
                error("undefined variable in %s: %s" % (where, arg))
            t = varDict[t[1:]]
            doDebug("%s from variable: %s" % (where, t))
    return t

#--- nextCounter()
def nextCounter():
    if os.access("counter", os.R_OK):
        f = open("counter")
        for line in f:
            line.strip()
            counter = int(line)
            break
        f.close()
        if (counter % 10) == 9:
            counter += 11
        else:
            counter = int(counter/10) * 10 + 10
        f = open("counter", "w")
        f.write("%d" % counter)
        f.close()

#
# Local commands executed on controller
#
LOCAL_CMD_DICT = {"END":0, "BEGIN":1, "WAIT":2, "PROCESS_EXP":3, "SOURCE":4,
        "HOST_SUFFIX":5, "SET":6, "IF":7, "IF_DEF":8, "RAND_WAIT":9, "DEBUG":10,
        "DEBUG_DISABLE":11, "DEBUG_RESTORE":12,"NEXT_COUNTER":13 }
CMD_ARG_DEFAULTS = {"order":0, "start":0, "ca":"reno", "dur":20, "delay":0,
        "instances":1, "req":"1M", "reply":"1", "stats":0,
        "localBuffer":0, "remoteBuffer":0, "test":"TCP_RR", "group":0,
        "expName":"Exp", "packets":10000, "exp":"COUNTER"}

#--- processCmd
def processCmd(line, funArgDict=None):
    global lastHost
    global lastExp
    global lastExpName
    global lastGroup
    global funDict
    global funLineList
    global funName
    global noRunFlag
    global defaultHostSuffix
    global getDataHostDict
    global varDict
    global descStr
    global otherStr
    global forList
    global forLoopList
    global forDict
    global forCount
    global forDefFlag
    global debugFlag
    global debugFlagSaved
    global forLoopPrint

    line = line.strip()
    if len(line) == 0:
        return ''

    # Ignore comments (start with '#')
    if line[0] == '#':
        return ''

    # Ignore comments at end of line
    pos = line.find('#')
    if pos > 0:
        line = line[:pos]
        line = line.strip()
        if len(line) == 0:
            return ''

    if line[-1] == "\\":
        return line[:-1]

    if line.find('ECHO') < 0:
        doDebug("")
        doDebug(line)

    findPos = 0
    newline = line
    while True:
        pos = newline.find('$', findPos)
        if pos >= 0:
            end = pos + 1
            while end < len(newline) and \
                  ( newline[end:end+1].isalnum() or newline[end:end+1] == "_"):
                end += 1
            val = getValue(newline[pos:end], funArgDict, line, False)
            newline = newline[0:pos] + val + newline[end:]
            if val[0] == '$':
                findPos = end
        else:
            break

    if False:
        print "   line:", line
        print "newline:", newline
        print " "

    args = newline.split()

    if len(args) == 0:
        return ''

    com = args[0]
    if funName != None:
        if com == "END" and len(args) > 1:
            if funName != args[1]:
                error('"END %s does not match "BEGIN %s"' % (args[1], funName))
            funDict[funName] = funLineList
            doDebug("New function:" + funName +"\n" + str(funLineList))
            funName = None
            funLineList = None
        else:
            funLineList.append(line)
        return ''


    if com != 'ECHO':
        doDebug("Command:" + com)

    if com == "DONE":
        if not forDefFlag:
            error("DONE encountered without a previous FOR")
        if forCount == 0:
            error("DONE but no previous FOR")
        if forLoopPrint:
            print "Done with FOR loop"
            doWait(2)
        forLoopList.append(forDict)
        indx = len(forLoopList) - 1
        line = "FORLOOP %d" % indx
        args = ["FORLOOP", str(indx)]
        com = "FORLOOP"
        forCount -= 1
        if forCount > 0:
            forDict = forStack.pop()
        else:
            forDefFlag = False
            if forLoopPrint:
                print "forDefFlag = FALSE"
                doWait(3)
                forLoopPrint = False

    if forDefFlag > 0 and com != 'FOR':
#    if forDefFlag > 0:
        forDict['lineList'].append(line)
        if forLoopPrint:
            print "Appending to forDict:" + line
            doWait(2)
        return ''

    # Local commands
    if com == "END" and len(args) == 1:
        doDebug("END command")
        nextCounter()
        exit(0)
    elif com == "IF":
        if len(args) < 2:
            error("IF should be followed by a variable")
        var = args[1]
        if var[-1] != ':':
            error("missing ':' in IF statement")
        var = var[0:-1]
        if var[0] != '$':
            num = float(var)
        else:
            if not var[1:] in varDict:
                num = 0
            else:
                num = float(varDict[var[1:]])
        if num != 0:
            indx = line.find(':')
            if indx < 0:
                error("Missing ':' in IF statement")
            doDebug("  IF statement, processing:" + line[indx+1:])
            return processCmd(line[indx+1:], funArgDict)
        else:
            return ''
    elif com == "DEBUG_DISABLE":
        debugFlagSaved = debugFlag
        debugFlag = False
        return ''
    elif com == "DEBUG_RESTORE":
        debugFlag = debugFlagSaved
        return ''
    elif com == "DEBUG":
        if len(args) < 2:
            error("DEBUG should be followed by 0, 1, T or F")
        val = args[1][0]
        if val == '0' or val == 'F' or val == 'f':
            debugFlag = False
        else:
            debugFlag = True
        return ''
    elif com == "NEXT_COUNTER":
        nextCounter()
        return ''
    elif com == "IF_DEF":
        if len(args) < 2:
            error("IF should be followed by a macro name")
        var = args[1]
        if var[-1] != ':':
            error("missing ':' in IF_DEF statement")
        var = var[0:-1]
        if var[0] != '$':
            if var in funDict:
                num = 1
            else:
                num = 0
        else:
            if not var[1:] in varDict:
                num = 0
            else:
                num = 1
        if num != 0:
            indx = line.find(':')
            if indx < 0:
                error("Missing ':' in IF_DEF statement")
            doDebug("  IF_DEF statement, processing:" + line[indx+1:])
            return processCmd(line[indx+1:], funArgDict)
        else:
            doDebug("  IF_DEF statement, not defined: " + var)
#            print "WARNING: IF_DEF statement, not defined: " + var
#            if debugFlag:
#                print "funDict:", funDict
            return ''
    elif com == "FOR":
        if len(args) < 5:
            error("FOR should be followed by 4 more arguments")
        forCount += 1
        varName = args[1]
        if args[2] != 'IN':
            error("'IN' missing in FOR statement")
        args[3] = getValue(args[3], funArgDict, "FOR")
        if args[3].find('..') > 0:
            x = args[3].split('..')
            if len(x) < 2:
                error("Range error in FOR loop: " + args[3])
            y = x[1].split(',')
            beg = int(x[0])
            end = int(y[0])
            if len(y) > 1:
                inc = int(y[1])
            else:
                inc = 1
            if (inc >= 0 and end < beg) or (inc <= 0 and end > beg):
                error("Range error in FOR loop: beg:%d end:%d inc:%d" %\
                        (beg, end, inc))
            if beg <= end:
                s = str(beg)
                beg += inc
                while beg <= end:
                    s += ',' + str(beg)
                    beg += inc
            else:
                s = ''
            args[3] = s
        varList = args[3].split(',')
        if forLoopPrint:
            print "FOR varName:", varName, " varList:", varList
        if args[4] != 'DO':
            error("'DO' missing in FOR statement")
        if forDict is not None:
            forStack.append(forDict)
        forDict = {}
        forDict['lineList'] = []
        forDict['varList'] = varList
        forDict['varName'] = varName
        forDefFlag = True
        return ''
    elif com == "FORLOOP":
        if len(args) < 2:
            error("FORLOOP missing FORLOOP ID")
        if forCount > 0:
            forStack.append(forDict)
        forCount += 1
        indx = int(args[1])
        if indx >= len(forLoopList):
            error("FORLOOP ID out of bounds")
        forDict = forLoopList[indx]
        forDict['varIndx'] = 0
#        print "FORLOOP varList:", forDict['varList']
        while forDict['varIndx'] < len(forDict['varList']):
            varDict[forDict['varName']] = forDict['varList'][forDict['varIndx']]
            forDict['varIndx'] += 1
#            print "  inside varIndx loop, varIndx:", forDict['varIndx']
            forDict['lineIndx'] = 0
            while forDict['lineIndx'] < len(forDict['lineList']):
                line = forDict['lineList'][forDict['lineIndx']]
                forDict['lineIndx'] += 1
#                print "  inside lineIndx loop, lineIndx:", forDict['lineIndx'], "line:", line
                processCmd(line, funArgDict)
#        print "  end of FORLOOP"
        forCount -= 1
        if forCount > 0:
            forDict = forStack.pop()
        return ''
    elif com == "DESC":
        if len(args) < 2:
            error("DESC should be followed by string")
        descStr = newline[5:]
        return ''
    elif com == "OTHER":
        if len(args) < 2:
            error("OTHER should be followed by string")
        otherStr = newline[6:]
        return ''
    elif com == "ECHO":
        for arg in args[1:]:
            if arg[0] == '$':
                if not arg[1:] in varDict:
                    error("Undefined variable in ECHO statement")
                arg = varDict[arg[1:]]
            if debugFlag:
                debugOutput.write("%s " % arg)
            else:
                print arg
        if debugFlag:
            debugOutput.write("\n")
        return ''
    elif com == "SET":
        if len(args) < 2:
            error("SET should be followed by 'var=value'")
        kv = args[1].split('=')
        if len(kv) < 2:
            error("SET should be followed by 'var=value'")
        kvals = kv[1].split(',')
        kval = ''
        i = 0
        for v in kvals:
            if v[0] == '$':
                if v[1:] not in varDict:
                    error("Undefined variable in SET: " + v)
                v = varDict[v[1:]]
            if v.find('/') > 0:
                f = v.split('/')
                v = str(int(f[0]) / int(f[1]))
            kval += v
            i += 1
            if i < len(kvals):
                kval += ','
        if kv[0] == "forLoopPrint":
            if kv[1] == "0":
                forLoopPrint = False
            else:
                forLoopPrint = True
            print "forLoopPrint: ", forLoopPrint
            doWait(3)
        else:
            varDict[kv[0]] = kval
        doDebug("SET %s to %s" % (kv[0], getValue(kval, funArgDict, "SET")))
        return ''
    elif com == "HOST_SUFFIX":
        if len(args) < 2:
            error("HOST_SUFFIX should be followed by host suffix")
        defaultHostSuffix = args[1]
        return ''
    elif com == "BEGIN":
        if len(args) == 1:
            error("BEGIN should be followed by a name")
        if funName != None:
            error("Cannot define a function within a function")
        if args[1] in funDict:
            print "Warning: redefining the function:", args[1]
        if args[1] in LOCAL_CMD_DICT:
            print "Warning: redefining a local command:", args[1]
        if args[1] in CMD_DICT:
            print "Warning: redefining a remote command:", args[1]
        funName = args[1]
        funLineList = []
        doDebug(">>> Starting definition of function " + funName)
        return ''
    elif com == "SOURCE":
        if len(args) < 2:
            error("Filename missing in SOURCE command")
        fin = open(args[1], 'r')
        useLine = ''
        for line in fin:
            line = useLine + ' ' + line
            useLine = processCmd(line, funArgDict)
        return ''
    elif com == "RUN":
        if len(args) < 2:
            error("RUN command missing function name")
        nameReps = args[1].split(',')
        fName = nameReps[0]
        if not fName in funDict:
            error(fName + " not in funDict!")
        lineList = funDict[fName]
        if len(nameReps) > 1:
            reps = nameReps[1]
            if reps[0] == '$':
                if not reps[1:] in varDict:
                    error("undefined variable in RUN command: " + reps)
                reps = varDict[reps[1:]]
                doDebug("RUN reps from variable: " + reps)
            reps = int(reps)
            if reps == 0:
                return ''
        else:
            reps = 1
        fArgDict = {}
        caList = [1]
        for arg in args[2:]:
            kv = arg.split('=')
            if len(kv) == 2:
                k, v = kv
                if v[0] == "$":
                    if not v[1:] in varDict:
                        error("Undefined variable in RUN argument list: " + v)
                    v = varDict[v[1:]]
                    doDebug("Variable in RUN argument list: %s=%s" % (k, v))
                fArgDict[k] = v
                if k == 'ca':
                    caList = v.split(',')
        while reps > 0:
            reps -= 1
            for ca in caList:
                doDebug("RUN: ca:%s from [%s]" % (ca, caList))
                if ca != 1:
                    fArgDict['ca'] = ca
                useLine = ''
                for line in lineList:
                    line = useLine + ' ' + line
                    useLine = processCmd(line, fArgDict)
        return ''
    elif com == "WAIT":
        if len(args) >= 2:
            t = getArg(args[1], funArgDict, com)
            if noRunFlag:
                doDebug("Would have waited:" + t)
            else:
                doWait(int(t))
                flushDebug()
        else:
            doDebug("WAIT command missing argument")
        return ''
    elif com == "RAND_WAIT":
        if len(args) >= 2:
            t0 = float(getArg(args[1], funArgDict, com))
            if len(args) >= 3:
                t1 = float(getArg(args[2], funArgDict, com))
            else:
                t1 = t0
                t0 = 0.0
            doRandomWait(t0, t1)
        else:
            doDebug("RAND_WAIT command missing argument")
        return ''
    elif com == "PROCESS_EXP":
        if noRunFlag:
            return ''
        exp = lastExp
        for arg in args[1:]:
            kv = arg.split("=")
            if len(kv) == 2 and kv[0] == "exp":
                exp = kv[1]
                if exp[0] == '$':
                    if not exp[1:] in varDict:
                        error("Undefined variable in PROCESS_EXP: " + exp)
                    exp = varDict[exp[1:]]
        processExp(exp)
        lastGroup = 1
        flushDebug()
        return ''

    # Remote commands
    argDict = {}

    # Initialize default argument values
    for key in CMD_ARG_DEFAULTS:
        argDict[key] = CMD_ARG_DEFAULTS[key]

    # Add previous host and exp as default argument values
    if len(lastHost) > 0:
        argDict["host"] = lastHost
    if len(lastExp) > 0:
        argDict["exp"] = lastExp
    if len(lastExpName) > 0:
        argDict["expName"] = lastExpName

    # parse command line arguments
    for arg in args[1:]:
        kv = arg.split("=")
        if len(kv) == 2:
            doDebug("  key:" + kv[0] + "  val:" +
                    getValue(kv[1], funArgDict, "Command"))
            k, v = kv
            if v[0] == "$":
                if funArgDict is not None and v[1:] in funArgDict:
                    v = funArgDict[v[1:]]
                    doDebug("Command line arg from fun Arg %s=%s" % (k,v))
                elif v[1:] in varDict:
                    v = varDict[v[1:]]
                    doDebug("Command line arg from variable %s=%s" % (k, v))
                else:
                    error("Function parameter %s missing" % v)
            argDict[k] = v

    # check for required arguments (exp and host)
    if not "exp" in argDict:
        if com == 'SET_MODULE_PARAMS' or com == 'EXIT' or \
                com == 'SET_SYSCTL' or com == 'SET_NETEM':
            argDict['exp'] = '0'
        else:
            error("exp argument missing in " + com)
    if not "host" in argDict:
        error("host argument missing in " + com)
    else:
        lastHost = argDict["host"]

    if argDict["exp"] == "counter" or argDict["exp"] == "COUNTER":
        if os.access("counter", os.R_OK):
            f = open("counter")
            for line in f:
                line.strip()
                counter = int(line)
                counter += 1
                break
            f.close()
        else:
            counter = 1
        f = open("counter", "w")
        f.write("%d" % counter)
        f.close()
        argDict["exp"] = str(counter)
    elif argDict["exp"] == "PREV":
        if len(lastExp) > 0:
            argDict["exp"] = lastExp
        else:
            error('exp="PREV" and lastExp not defined!')

    lastExp = argDict["exp"]
    lastExpName = argDict["expName"]

    exp = int(argDict["exp"])
    host = argDict["host"]

# Do not run GET_DATA for the same host unecessarily
    if com == "DO_CLIENT":
        getDataHostDict = {}
    elif com == "DO_SERVER":
        getDataHostDict = {}
    elif com == "GET_DATA":
        if host in getDataHostDict:
            doDebug("Skipping GET_DATA for " + host)
            return ''
        else:
            getDataHostDict[host] = 1

    # Add default DC to host if necessary
    p = host.find(".")
    if p < 0:
        host += "." + defaultHostSuffix
        lastHost = host
        argDict["host"] = host
    sock = getSocket(host)
    if sock == None:
        return ''

    if com in CMD_DICT:
        rv = CMD_DICT[com](sock, argDict)
        if rv <= 0:
            doDebug("%s returns %d, closing socket!" % (com, rv))
            closeClientSocket(sock)
    else:
        doDebug("Unknown command: " + com)
        return ''

    msgType, msgData = rcvMsg(sock)
    if msgType == ERROR:
        doDebug("Reply: ERROR (socket closed)")
        closeClientSocket(sock, False)
    else:
        doDebug("Reply:" + MSG_NAME[msgType] + " " + str(msgData))
        if noRunFlag:
            return ''
        if com == "GET_DATA" and msgType != MSG_FILE:
                doDebug("Error: GET_DATA commands does not return MSG_FILE")
        elif msgType == MSG_FILE:
                filename, size = msgData
                filename = cleanStr(filename)
                readFile(sock, filename, size)
    return ''

#--- Main
init()
HostName = socket.gethostname()
HostName = HostName[0: HostName.find('.')]

opt_list = ["debug="]

try:
    opts, args = getopt.getopt(sys.argv[1:], 'dhns', opt_list)
except getopt.GetoptError, err:
    doDebug(str(err))
    error(str(err))

#print >>flog, 'opts = ', opts
#print >>flog, 'args = ', args

for opt in opts:
    key = opt[0]
    val = opt[1]
    if key == '-h':
        printUsage()
        exit(0)
    elif key == '-s':
        serverFlag = True
        # startNetserver()
    elif key == '-d':
        debugFlag = True
        debugFlagSaved = True
    elif key == '-n':
        noRunFlag = True
    elif key == "--debug":
        debugFlag = True
        debugOutput = open(val, "a")
        debugOutput.write("-----\n")
    elif key == "--port":
        serverPort = int(val)

if serverFlag:
    # Read list of allowed client ipv6 addresses
    clientFin = open('clients.txt', 'r')
    for line in clientFin:
        line = line.strip()
        if len(line) > 0:
            doDebug("Adding to client list: " + line)
            clientDict[line] = 1
    clientFin.close()

    # Create passive socket
    serverSocket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    serverSocket.bind((socket.gethostname(), serverPort))
    serverSocket.listen(MAX_PORTS)
    readList = [serverSocket]
    #while True:
    #accept connections from outside
    doDebug("Waiting for client to connect")
#	(clientSocket, address) = serverSocket.accept()
#	print "Server connected:", clientSocket, address
    waitCount = 0
    while True:
        readyRead, readyWrite, inError = \
            select.select(readList, [], [], 60)
        flushDebug()
        if len(readyRead) > 0:
            waitCount = 0
            for sock in readyRead:
                if sock == serverSocket:
                    (clientSocket, address) = serverSocket.accept()
                    address = str(address[0])
                    doDebug("Server connected:" + address)
                    if address not in clientDict:
                        doDebug("Unknown client %s, ignoring" % address)
                        flushDebug()
                        continue
                    readList.append(clientSocket)
                    socketDict[id(clientSocket)] = address
                    socketBufferDict[id(clientSocket)] = ''
                else:
                    doDebug("  readyRead socket:" + sockName(sock))
                    msgType, msgData = rcvMsg(sock)
                    if msgType == ERROR:
                        closeAServerSocket(sock, 0)
                        continue
                    if processMsg(sock, msgType, msgData) <= 0:
                        readList.remove(sock)
        else:
            waitCount += 1
            if waitCount > 14400:
                doDebug("  Terminating after idling for 10 days")
                exit(0)

else:
    doDebug("Enter commands:")
    useLine = ''
    for line in sys.stdin:
        line = useLine + ' ' + line
        useLine = processCmd(line)
