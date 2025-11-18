#!/bin/bash

[ "$1" == '-i' ] && apk add py3-netifaces py3-ipaddress py3-requests py3-lxml

base_dir=`dirname "$PWD/$0/"| sed s/'\/\.\/'/'\/'/g| sed s/'\/\.$'/'\/'/g| sed s/'\/$'/''/g`
cp "${base_dir}/../auto_detect.py" "${base_dir}/../const.py" "${base_dir}"
python auto_detect.py
rm "${base_dir}/auto_detect.py" "${base_dir}/const.py"







