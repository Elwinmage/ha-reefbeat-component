#!/bin/bash
val=`head -n 2 reports/coverage.xml |grep -Eo 'line-rate="\b(0(\.[0-9]+)?|1(\.0+)?)\b"' |cut  -d '"' -f 2`
percent=`echo "${val} * 100" |bc`
echo "${percent}%"
if [ $(echo "${percent} >= 100" | bc -l) -eq 1 ]; then
    exit 0
else
    exit 1
fi
