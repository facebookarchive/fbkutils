#!/bin/bash
#
# ./setSysctl.sh <sysctl> <value>


sysctl -q -w $1="$2"

