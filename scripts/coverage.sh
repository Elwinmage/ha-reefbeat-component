#!/bin/bash
val=`head -n 2 reports/coverage.xml |grep -Eo 'line-rate="\b(0(\.[0-9]+)?|1(\.0+)?)\b"' |cut -d '"' -f 2`

echo ${val} |awk '{printf "%.2f%%\n", $1 * 100}'
