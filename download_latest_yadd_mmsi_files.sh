#!/usr/bin/bash

# Grap <a href=./tmp/yadd_mmsi_coast_1762488983825455756.txt>
curl https://www.yaddnet.org/pages/php/test/mmsi_coast.php > /tmp/mmsi_coast.php
DL_FILE=$(cat /tmp/mmsi_coast.php | sed -n 's|.*[<]a href=\.\(.*\)[>]File .*|\1|p')
wget -O YADDcoast.txt https://www.yaddnet.org/pages/php/test/${DL_FILE}

# Grap <a href=./tmp/yadd_mmsi_coast_1762488983825455756.txt>
curl https://www.yaddnet.org/pages/php/mmsi_shipname.php > /tmp/mmsi_shipname.php
DL_FILE=$(cat /tmp/mmsi_shipname.php | sed -n 's|.*[<]a href=\.\(.*\)[>]File .*|\1|p')
wget -O YADDship.txt https://www.yaddnet.org/pages/php/${DL_FILE}

