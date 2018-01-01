#!/bin/bash

if [ "$#" -eq "0" ] ; then
  d="."
else
  d=$1
fi

hn=`hostname | grep -o '^[a-z0-9]*'`

#echo "Doing doSs.sh to $d/ss.$hn" >> /root/nettest/out

n=0
echo "-----------------" >> $d/ss.$hn
while [ "$n" -lt "30" ] ; do ss -6 -i -t -m -o -e "( sport = :55601 )" >> $d/ss.$hn ; n=$[n+1] ; usleep 200000 ; done


