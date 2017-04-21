#!/bin/bash
#
# Given experiment directories as arguments, this script will copy
# the most important parts to a subdirectory within the "Small" directory
# and then tar them.
# This simplifies copying to another machine.
# 
# Don't forget to also copy exp.html and exp.csv
#
if ! [ -a Small ] ; then
  mkdir Small
fi

p=`pwd`
d=${p##*/}
if ! [ -a Small/$d ] ; then
  mkdir Small/$d
fi

rm -fR Small/$d/*

args="$@"
for a in $args ; do
	mkdir Small/$d/$a
	cp $a/*.html Small/$d/$a
	cp $a/*.jpg Small/$d/$a
done

cd Small
cp ../*.html ../*.csv $d
tar -zcf ../exp.tgz $d
cd ..

