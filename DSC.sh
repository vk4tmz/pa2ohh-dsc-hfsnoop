#!/bin/sh

# Start DSC
lxterminal -l -e 'python3 DSCHFsnoop.py ; /bin/sh ' &
lxterminal -l -e 'python3 FTPsnoop.py ; /bin/sh ' &
