#!/bin/bash
#
# ./setParam.sh <module> <param> <value>
 
echo $3 > /sys/module/$1/parameters/$2

