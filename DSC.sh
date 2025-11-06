#!/bin/sh

# Start DSC
cd /home/pa2ohh/P3-DSCHFsnoop/Python3/
lxterminal -l -e 'python3 DSCHFsnoop-v02a.py ; /bin/sh ' &
lxterminal -l -e 'python3 FTPsnoop-v01a.py ; /bin/sh ' &
