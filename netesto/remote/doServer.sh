#!/bin/bash

exp="ZZ"
order="0"
name="$0"
args="$@"

hostname=`hostname`
hn=`hostname | grep -o '^[a-z0-9]*'`
kernel=`uname -r`

#-- Usage
printUsage() {
	echo "USAGE: $name --exp=<#> [--order=<#>] [-beg] [-end] [-s] [--start=<#>] [-h]"
	echo "     Where: --exp    Refers to experiment number. A directory will"
	echo "                     will be created to store results"
	echo "            --beg    This is being called at beginning of experiment"
	echo "                     subdirectory '0' will store initial stats"
	echo "            --end    This is being called at end of experiment"
	echo "                     subdirectory '1' will store final stats'"
	echo "            --start  !=0 to start netserver if not already running"
	echo "            -s       start netserver if not already running"
	echo "            --order  ==0 => beg, !=0 => end."
	echo ""
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

#-- processArgs
processArgs() {
  for i in $args ; do
    case $i in
    -e=*|--exp=*)
      exp="${i#*=}"
      ;;
		--order=*)
			order="${i#*=}"
			;;
    --beg)
      order="0"
      ;;
    --end)
      order="1"
      ;;
		-s)
			startServer=1
			;;
		--start=*)
			startServer="${i#*=}"
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

order="3"
startServer=0

processArgs

#tcpRmem=`sysctl net.ipv4.tcp_rmem | awk '{ print $5 }'`
#if [ "$tcpRmem" -lt 20000000 ] ; then
#  sysctl -w net.ipv4.tcp_rmem="4096 262144 20971520"
#fi
#  
#tcpWmem=`sysctl net.ipv4.tcp_wmem | awk '{ print $5 }'`
#if [ "$tcpWmem" -lt 20000000 ] ; then
#  sysctl -w net.ipv4.tcp_wmem="4096 262144 20971520"
#fi

if [ "$exp" == "ZZ" ] ; then
  echo "ERROR, must specify '--exp=<..>'"
	echo ""
  exit
fi

if [ "$order" != "3" ] ; then
  if ! [ -a $exp ] ; then
    mkdir $exp
  fi

  if ! [ -a $exp/$order ] ; then
    mkdir $exp/$order
  fi

  getStaticStats $exp/$order
fi

if [ "$startServer" != "0" ] ; then
  netserverPid=`ps ax | grep netserver | grep --invert-match "grep" | awk '{ print $1 }'`
	if [ "$netserverPid" == "" ] ; then
		if [ -a ./netserver ] ; then
			./netserver
		else
			netserver
		fi
    sleep 3
	fi
fi

if [ "$order" == "0" ] ; then
#  echo "Calling doSs.sh $exp" >> /root/nettest/out
  ( sleep 1 ; ./doSs.sh $exp ) &
fi


