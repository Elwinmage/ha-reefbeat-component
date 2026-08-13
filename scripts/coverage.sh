#!/bin/bash
head -n 2 reports/coverage.xml |grep -Eo 'line-rate="\b(0(\.[0-9]+)?|1(\.0+)?)\b"'
