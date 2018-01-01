#!/bin/bash


#-- Main variables
#set -x
debug=1
portBase=31850

name="$0"
args="$@"

hostname=`hostname`
hn=`hostname | grep -o '^[a-z0-9]*'`
kernel=`uname -r`

#-- doDebug
doDebug() {
  if [ $debug -ne "0" ] ; then
		echo "$1"
	fi
}

#-- Usage
printUsage() {
	echo "USAGE: $name --exp=<#> [ARGS]"
  echo '       [(-b|--local_buffer)=<send/receive buffer size in bytes>]'
  echo '       [(-B|--remote_buffer)=<send/receive buffer size in bytes>]'
  echo '       [(-c|--ca)==<tcp congestion control. Expamples reno,cubic>]'
  echo '       [(-d|--dur)=<duration in seconds>]'
  echo '       [(-D|--delay)=<delay in seconds before starting tranfers>]'
  echo '       [(-g|--group)=<group #, used for grouping runs>]'
  echo '       [(-i|--instances)=<# of netperf instances to run>]'
  echo '       [(-n|--notes)=<notes>]'
  echo '       [(-N|--name)=<experiment name>]'
  echo '       [(-r|--req)=<Request size in bytes. Ex 1M>]'
  echo '       [(-R|--reply)=<Reply size in bytes. Ex 1>]'
  echo '       [(-s|--server)=fhost running netserver>]'
  echo '       [(-S|--stats)=<1 to get stats, 0 not to>]'
	echo '       [(-t|--test)=<test name. One of TCP_RR or TCP_STREAM>]'
  echo '       [(-h|--help)]'
	echo ''
}

#-- processArgs
processArgs() {
  for i in $args ; do
    case $i in
    -b=*|--local_buffer=*)
      localBuffer="${i#*=}"
			doDebug "localBuffer:$localBuffer"
      ;;
    -B=*|--remote_buffer=*)
      remoteBuffer="${i#*=}"
      doDebug "remoteBuffer:$remoteBuffer"
      ;;
    -c=*|--ca=*)
      ca="${i#*=}"
      if [ "$ca" == "dctcp" ] ; then
        remCa=$ca
      elif [ "$ca" == "nv" ] ; then
        remCa="nv"
      else
        remCa="cubic"
      fi
      doDebug "ca:$ca, remCa:$remCa"
      ;;
    -d=*|--dur=*)
      dur="${i#*=}"
      doDebug "dur:$dur"
      ;;
    -D=*|--delay=*)
      delay="${i#*=}"
      doDebug "delay:$delay"
      ;;
    -e=*|--exp=*)
      exp="${i#*=}"
			doDebug "exp:$exp"
      ;;
    -g=*|--group=*)
      group="${i#*=}"
      doDebug "group:$group"
      ;;
    -i=*|--instances=*)
      instances="${i#*=}"
			doDebug "instances:$instances"
      ;;
		-n=*|--notes=*)
			notes="${i#*=}"
			doDebug "notes:$notes"
			;;
    -N=*|--name=*)
      expName="${i#*=}"
      doDebug "expName:$expName"
      ;;
    -r=*|--req=*)
      req="${i#*=}"
      doDebug "req:$req"
      ;;
    -R=*|--reply=*)
      reply="${i#*=}"
      doDebug "reply:$reply"
      ;;
    -s=*|--server=*)
      server="${i#*=}"
      doDebug "server:$server"
      ;;
		-S)
			getStats=1
		  doDebug "getStats:$getStats"
			;;
		--stats=*)
      getStats="${i#*=}"
      doDebug "getStats:$getStats"
      ;;
		-t=*|--test=*)
			testName="${i#*=}"
		  doDebug "test:$testName"
		  ;;
    -h|--help)
      printUsage
      exit
      ;;
    *)
      echo "unknown arg: $i"
      ;;
    esac
  done
}

#-- getStaticStats
getStaticStats() {
  cat /proc/net/snmp > $1/$hn.snmp
  cat /proc/net/snmp6 > $1/$hn.snmp6
  cat /proc/net/netstat > $1/$hn.netstat
  sysctl -a -e 2> /dev/null > $1/$hn.sysctl
  top -n 1 -b > $1/$hn.top
  ifconfig eth0 > $1/$hn.ifconfig
  ethtool -S eth0 > $1/$hn.ethtool-S
  ethtool -a eth0 > $1/$hn.ethtool-a
  ethtool -c eth0 > $1/$hn.ethtool-c
  ethtool -k eth0 > $1/$hn.ethtool-k
  echo "exp:$exp" > $1/$hn.info
  echo "hn:$hn" >> $1/$hn.info
  echo "hostname:$hostname" >> $1/$hn.info
  echo "kernel:$kernel" >> $1/$hn.info
}

#-- runNetperf <output-dir>
runNetperf() {
#	tcpRmem=`sysctl net.ipv4.tcp_rmem | awk '{ print $5 }'`
#	if [ "$tcpRmem" -lt 20000000 ] ; then
#		sysctl -w net.ipv4.tcp_rmem="4096 262144 20971520"
#	fi
#	
#	tcpWmem=`sysctl net.ipv4.tcp_wmem | awk '{ print $5 }'`
#	if [ "$tcpWmem" -lt 20000000 ] ; then
#		sysctl -w net.ipv4.tcp_wmem="4096 262144 20971520"
#	fi

	if [ -e ./netperf ] ; then
		netperfBin="./netperf"
	else
		netperfBin="netperf"
	fi
  if [ "$localBuffer" -gt "0" ] ; then
    aLocalBuffer="-s $localBuffer"
	else
		aLocalBuffer=""
  fi
  if [ "$remoteBuffer" -gt "0" ] ; then
    aRemoteBuffer="-S $remoteBuffer"
	else
		aRemoteBuffer=""
  fi
  if [ "$testName" == "TCP_RR" ] ; then
		aReqReply="-r $req,$reply"
	else
		aReqReply=""
	fi
	echo "CA=$ca" > $1/netperf.$hsni.out
	echo "FLOW=$hsni">> $1/netperf.$hsni.out
  ($netperfBin -H $server -l $dur -C -c -j -t $testName -D 0.2,\
   -- $aReqReply -K $ca,$remCa -k netperf.fields -P $port \
	    $aLocalBuffer $aRemoteBuffer \
   >> $1/netperf.$hsni.out \
  )&
  doDebug "$netperfBin -H $server -l $dur -C -c -j -t $testname -D 0.2,"
  doDebug "    -- -r $req,$reply -K $ca,$remCa -k netperf.fields -P $port"
	doDebug "       $aLocalBuffer $aRemoteBuffer"
  doDebug "    > $1/netperf.$hsni.out"
}

#-- getTcpInfo <output-dir>
getTcpInfo() {
  major=${kernel:0:1}
  minor=${kernel:2:2}
  dur1=$[dur - 1]
  use_ss=1

  doDebug "use_ss:$use_ss"
  n=0
  l=$[dur1*5]
  ( sleep 1 ; while [ "$n" -lt "$l" ] ; \
    do ss -6 -i -t -m -o state established "( sport = :$port )" >> \
    $1/ss.$hsni.out ; n=$[n+1] ; usleep 200000 ; done \
  )&
}

#-- getCpuInfo <output-dir>
getCpuInfo() {
  dur1=$[dur - 1]
  ( sleep 1 ; iostat -c 1 $dur1 > $1/iostat.$hn.out )&  
}

#-- getPingInfo <output-dir>
getPingInfo() {
  dur1=$[dur - 1]
  ( sleep 1 ; ping6 -i 0.2 -q -w $dur $server > $1/ping.$hsn.out )&
}

#--- writeRunInfo <output-dir>
writeRunInfo() {
	echo "writeRunInfo $1"
	echo "exp:$exp" > $1
  echo "expName:$expName" >> $1
  echo "host:$hn" >> $1
  echo "server:$server" >> $1
  echo "group:$group" >> $1
  echo "instances:$instances" >> $1
  echo "instance:$instance" >> $1
  echo "dur:$dur" >> $1
  echo "delay:$delay" >> $1
  echo "req:$req" >> $1
	echo "reply:$reply" >> $1
  echo "ca:$ca" >> $1
}

#--- writeExpInfo <output-dir>
writeExpInfo() {
	partialHost=`echo $hostname | egrep -o '^[a-z0-9]*'`
	partialServer=`echo $server | egrep -o '^[a-z0-9]*'`
  echo "exp:$exp.$group" > $1
  echo "expName:$expName" >> $1
	echo "test:$testName" >> $1
  echo "host:$partialHost" >> $1
	echo "fullHost:$hostname" >> $1
  echo "server:$partialServer" >> $1
	echo "fullServer:$server" >> $1
  echo "group:$group" >> $1
  echo "kernel:$kernel" >> $1
  echo "instances:$instances" >> $1
  echo "instance:$instance" >> $1
  echo "dur:$dur" >> $1
  echo "delay:$delay" >> $1
  echo "req:$req" >> $1
  echo "reply:$reply" >> $1
  echo "ca:$ca" >> $1
  if [ "$ca" == "nv" ] ; then
    params=`ls /sys/module/tcp_nv/parameters`
    for p in $params ; do
      v=`cat /sys/module/tcp_nv/parameters/$p`
      echo "$p:$v" >> $1
    done
  fi

}

#-- writeRunResults <dir>
writeRunResults() {
  echo "localCpu:$localCpu" >> $1
  echo "remoteCpu:$remoteCpu" >> $1
  echo "rate:$rate" >> $1
  echo "cwnd:$avgCwnd" >> $1
  echo "rtt:$avgRtt" >> $1
  if [ "$use_ss" -eq "0" ] ; then
    echo "unacked:$unacked" >> $1
    echo "lost:$lost" >> $1
    echo "retrans:$retrans" >> $1
    echo "retrans_total:$retrans_total" >> $1
  fi
}

#-- writeExpResults
writeExpResults() {
  echo "localCpu:$localCpu" >> $1
	echo "remoteCpu:$remoteCpu" >> $1
  echo "rate:$rate" >> $1
  echo "rateMin:$rate_min" >> $1
  echo "rateMax:$rate_max" >> $1
	echo "localRetrans:$localRetrans" >> $1
	echo "remoteRetrans:$remoteRetrans" >> $1
	echo "minLatency:$minLatency" >> $1
	echo "maxLatency:$maxLatency" >> $1
	echo "meanLatency:$meanLatency" >> $1
	echo "p50Latency:$p50Latency" >> $1
	echo "p90Latency:$p90Latency" >> $1
	echo "p99Latency:$p99Latency" >> $1
	echo "p999Latency:$p999Latency" >> $1
  echo "cwnd:$avgCwnd" >> $1
  echo "rtt:$avgRtt" >> $1
  echo "pingRtt:$pingRtt" >> $1
  if [ "$use_ss" -eq "0" ] ; then
    echo "unacked:$unacked" >> $1
    echo "lost:$lost" >> $1
    echo "retrans:$retrans" >> $1
    echo "retrans_total:$retrans_total" >> $1
  fi
	echo "tcpRmem:$tcpRmem" >> $1
	echo "tcpWmem:$tcpWmem" >> $1
  echo "tso:$tso" >> $1
  echo "lro:$lro" >> $1
  echo "gso:$gso" >> $1
  echo "gro:$gro" >> $1
  echo "rx-frames:$rxFrames" >> $1
  echo "tx-frames:$txFrames" >> $1
  echo "adaptive-rx:$adaptiveRx" >> $1
#  echo "rx-usecs-high:$rxUsecsHigh" >> $1
#  echo "tx-usecs-high:$txUsecsHigh" >> $1
  echo "client-rx-packets:$rxPackets" >> $1
  echo "client-tx-packets:$txPackets" >> $1
  echo "client-rx-bytes:$rxBytes" >> $1
  echo "client-tx-bytes:$txBytes">> $1
  echo "client-tx-packet-len:$txPacketSizeClients" >> $1
  echo "client-rx-packet-len:$rxPacketSizeClients" >> $1
	echo "-----" >> $1
}

#-- initProcessInfo
initProcessInfo() {
  rate_min=99999999
  rate_max=0
  rate_sum=0
  cwnd_sum=0
  rtt_sum=0
  lost_sum=0
  retrans_sum=0
  retrans_total_sum=0
}

#-- processTcpInfo <dir>
processTcpInfo () {
  if [ "$use_ss" -eq "0" ] ; then
    infoFn="$1/monitor"
  else
    infoFn="$1/ss"
  fi

  avgCwnd=`cat $infoFn.$hsni.out | grep -o ' cwnd:[0-9]*' | grep -o '[0-9]*' \
           | awk '{ cwnd = cwnd + $1 } END { printf "%.0f\n",cwnd/NR}'`
  cwnd_sum=$[cwnd_sum + avgCwnd]

  avgRtt=`cat $infoFn.$hsni.out | grep -o ' rtt:[0-9.]*' | grep -o '[0-9.]*' \
          | awk '{ sum = sum + $1 } END { printf "%.0f\n",1000*sum/NR}'`
  rtt_sum=$[rtt_sum + avgRtt]

  if [ "$use_ss" -eq "0" ] ; then
    ca=`cat $infoFn.$hsni.out | grep -o -m 1 ' ca:[a-z_]*' `
    ca=${ca:4}
    unacked=`cat $infoFn.$hsni.out | grep -o ' unacked:[0-9]*' \
             | grep -o '[0-9]*' \
             | awk '{ cwnd = cwnd + $1 } END { printf "%.0f\n",cwnd/NR}'`

    lost=`tail -n 1 $1/monitor.$hsni.out | grep -o ' lost:[0-9]*' | grep -o '[0-9]*'`
    lost_sum=$[lost_sum + lost]
    retrans=`tail -n 1 $1/monitor.$hsni.out | grep -o ' retrans:[0-9]*' \
             | grep -o '[0-9]*'`
    retrans_sum=$[retrans_sum + retrans]

    retrans_total=`tail -n 1 $1/monitor.$hsni.out \
                   | grep -o ' retrans_total:[0-9]*' | grep -o '[0-9]*'`
    retrans_total_sum=$[retrans_total_sum + retrans_total]
  fi
}

#-- getNetperfVal <dir> <key>
getNetperfVal() {
	rv=`grep "$2" $1/netperf.$hsni.out | egrep -o "=[0-9.]*" \
		  | egrep -o "[0-9.]*"`
}

#-- processNetperfInfo <dir>
processNetperfInfo() {
  getNetperfVal $1 LOCAL_SEND_THROUGHPUT ; rate=$rv
  echo "rate: $rate" >> $hsn.client.out 
  rate_int=`echo "$rate" | egrep -o "^[0-9]*"`
  rate100=`echo "$rate * 100" | bc -q -i | tail -1 | grep -o "[0-9]*" | head -1`
  echo "rate100: $rate100" >> $hsn.client.out
  rate_sum=$[rate_sum + rate100]
  echo "rate_sum: $rate_sum" >> $hsn.client.out
#  rate_sum=`echo "$rate_sum + $rate" | bc -q -i`
  if [ $rate100 -gt $rate_max ] ; then
    rate_max=$rate100
  fi
  echo "rate_max: $rate_max" >> $hsn.client.out
  if [ $rate100 -lt $rate_min ] ; then
    rate_min=$rate100
  fi
  echo "rate_min: $rate_min" >> $hsn.client.out

	getNetperfVal $1 LOCAL_CPU_UTIL ; localCpu=$rv
	getNetperfVal $1 REMOTE_CPU_UTIL ; remoteCpu=$rv
	getNetperfVal $1 LOCAL_TRANSPORT_RETRANS ; localRetrans=$rv
	getNetperfVal $1 REMOTE_TRANSPORT_RETRANS ; remoteRetrans=$rv
	getNetperfVal $1 MIN_LATENCY ; minLatency=$rv
	getNetperfVal $1 MAX_LATENCY ; maxLatency=$rv
	getNetperfVal $1 MEAN_LATENCY ; meanLatency=$rv
	getNetperfVal $1 P50_LATENCY ; p50Latency=$rv
	getNetperfVal $1 P90_LATENCY ; p90Latency=$rv
	getNetperfVal $1 P99_LATENCY ; p99Latency=$rv
	getNetperfVal $1 P999_LATENCY ; p999Latency=$rv
}

#-- getDiff file0 file1 field -> rv=field[1]-field[0]
getDiff() {
  v0=`cat $1 | grep -m 1 "$3" | awk '{ print $2 }'`
  v1=`cat $2 | grep -m 1 "$3" | awk '{ print $2 }'` 
  rv=$[v1-v0]
}

#-- getOtherInfo <dir>
getOtherInfo() {
  pingRtt=`grep "min/avg" $1/ping.$hsn.out | grep -o '/[0-9.]*/' | grep -o '[0-9.]*' | awk '{ printf "%.0f",$1*1000 }'`

	file="$hn.ethtool-S"
	f0="$exp/0/$file"
  f1="$exp/1/$file"
	if [ -e $f1 ] ; then
		getDiff $f0 $f1 "rx_packets" ; rxPackets=$rv
		getDiff $f0 $f1 "tx_packets" ; txPackets=$rv
		getDiff $f0 $f1 "rx_bytes" ; rxBytes=$rv
		getDiff $f0 $f1 "tx_bytes" ; txBytes=$rv
		txPacketSizeClients=`dc -e "$txBytes $txPackets / p"`
		rxPacketSizeClients=`dc -e "$rxBytes $rxPackets / p"`
	else
		rxPackets=0
		txPackets=0
		rxBytes=0
		txBytes=0
		txPacketSizeClients=0
		rxPacketSizeClients=0
	fi

  tso=`cat $1/0/$hn.ethtool-k | grep tcp-segmentation-offload \
       | awk ' { print $2 } '`
  lro=`cat $1/0/$hn.ethtool-k | grep large-receive-offload | awk ' { print $2 } '`
  gso=`cat $1/0/$hn.ethtool-k | grep generic-segmentation-offload \
       | awk ' { print $2 } '`
  gro=`cat $1/0/$hn.ethtool-k | grep generic-receive-offload\
       | awk ' { print $2 } '`
  adaptiveRx=`cat $1/0/$hn.ethtool-c | grep 'Adaptive RX:' | awk ' { print $3 } '`
  rxUsecs=`cat $1/0/$hn.ethtool-c | grep 'rx-usecs:' | awk ' { print $2 } '`
  txUsecs=`cat $1/0/$hn.ethtool-c | grep 'tx-usecs:' | awk ' { print $2 } '`
  rxFrames=`cat $1/0/$hn.ethtool-c | grep 'rx-frames:' | awk ' { print $2 } '`
  txFrames=`cat $1/0/$hn.ethtool-c | grep 'tx-frames:' | awk ' { print $2 } '`

  tcpRmem=`sysctl net.ipv4.tcp_rmem | awk '{ print $5 }'`
	tcpWmem=`sysctl net.ipv4.tcp_wmem | awk '{ print $5 }'`
}

#-- Main

#set value of default args
expName="Exp"
group=1
localBuffer=0
remoteBuffer=0
ca="reno"
remCa="reno"
dur="20"
delay="0"
instances="0"
req="1M"
reply=1
getStats="0"
server="YY"
exp="ZZ"
testName="TCP_RR"

processArgs

if [ "$delay" -gt "0" ] ; then
	sleep $delay
fi

# check for required input
if [ "$exp" == "ZZ" ] ; then
  echo "ERROR, must specify '--exp=<..>'"
	echo ""
  exit
fi

if [ "$server" == "YY" ] ; then
  echo "ERROR, must specify '--server=<host>'"
  echo ""
  exit
fi

ip tcp_metrics flush all > /dev/null 2>&1

sn=`echo $server | grep -o '^[a-zA-Z0-9]*'`
if [ "$server" == "$sn" ] ; then
  server="$server.prn2.facebook.com"
fi
hsn="$hn-$sn-$group"

if ! [ -a $exp ] ; then
  mkdir $exp
fi

if [ "$getStats" -gt "0" ] ; then
  if ! [ -a $exp/0 ] ; then
    mkdir $exp/0
  fi
  getStaticStats $exp/0
  if [ "$dur" -gt "0" ] ; then
    getCpuInfo $exp
  fi
fi

if [ "$dur" -gt 0 ] ; then
  getPingInfo $exp
fi

instance=1
while [ $instance -le $instances ] ; do
  hsni="$hn-$sn-$group-$instance"
	port=$[(32*(group - 1)) + instance + portBase]
  runNetperf $exp
  getTcpInfo $exp
  echo "$hn $sn $instance $port" >> $exp/runs.out
	writeRunInfo "$exp/$hsni.run"
  instance=$[instance + 1]
done

if [ "$dur" -gt "0" ] ; then
  sleep $dur

  sleep 12

  if [ "$getStats" -gt "0" ] ; then
    if ! [ -a $exp/1 ] ; then
      mkdir $exp/1
    fi
    getStaticStats $exp/1
  fi
fi

doDebug "After netperf"

initProcessInfo

instance=1
while [ $instance -le $instances ] ; do
  hsni=$hn-$sn-$group-$instance
  processTcpInfo $exp
  processNetperfInfo $exp
  writeRunResults $exp/$hsni.run
  instance=$[instance + 1]
done

rate=`echo "scale=1 ; ($rate_sum + 5) / 100.0" | bc -q -i | tail -1`
echo "rate final: $rate" >> $hsn.client.out
rate_min=`echo "scale=1 ; ($rate_min + 5) / 100.0" | bc -q -i | tail -1`
echo "rate_min final: $rate_min" >> $hsn.client.out
rate_max=`echo "scale=1 ; ($rate_max + 5) / 100.0" | bc -q -i | tail -1`
echo "rate_max final: $rate_max" >> $hsn.client.out
#avgCwnd=$[cwnd_sum / instances]
avgCwnd=`echo $cwnd_sum $instances | awk '{ r = $1 / $2 } END { printf "%.1f\n",r }'`
#avgRtt=$[rtt_sum / instances]
avgRtt=`echo $rtt_sum $instances | awk '{ r = $1 / $2 } END { printf "%.1f\n",r }'`
lost=$lost_sum
retrans=$retrans_sum
retrans_total=$retrans_total_sum

pingRtt=`grep "min/avg" $exp/ping.$hsn.out | grep -o '/[0-9.]*/' | grep -o '[0-9.]*' | awk '{ printf "%.0f",$1*1000 }'`

instance=all
writeExpInfo $exp/$hsn.exp.out
getOtherInfo $exp

writeExpResults $exp/$hsn.exp.out

