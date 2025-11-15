
import sys

sys.path.insert(0, '..')
sys.path.insert(0, '.')

from util.utils import TENunit
from modem.Bits import BitQueue
from decoder.dsc.decoder import HLINE
from decoder.dsc.messages.message_factory import DSCMessageFactory
from decoder.dsc.config import DscConfig
from decoder.dsc.db.DSCDatabases import DscDatabases

from collections import deque

# Convert Test data saved from running  the Application to strYBY data and pump these through the DSCMessageFactory
# Collate all capture msg into single file
#
# find ./data -name "msgdata*" -exec cat {} \; > /tmp/dsc_test_msgs.txt
#

def generateDSCMessageSequence(msg) -> list[int]:
    seq = [0] * 200

    # FS
    i=0
    seq[0] = msg[0]
    seq[5] = msg[0]
    seq[1] = 105
    seq[2] = msg[0]
    seq[7] = msg[0]
    seq[3] = 104
    

    i = 4
    # process between FS and last DX, ECC
    for v in msg[1:len(msg)-2]:
        seq[i] = v
        seq[i+5] = v 

        i += 2
    
    dx = msg[-2]
    ecc = msg[-1]

    seq[i] = dx
    seq[i+4] = dx
    seq[i+5] = dx
    seq[i+6] = dx

    seq[i+2] = ecc
    seq[i+2+5] = ecc

    seq_len = i + 7

    seq = seq[:seq_len+1]

    return seq

##########
# Main
##########

leadin_seq = "Y" * 15

dsc_phasing_dxrx = []
for rx in range(111,105,-1):
    dsc_phasing_dxrx.extend([125, rx])

print(f"LEADIN: {leadin_seq}")
print(f"PHASING: {dsc_phasing_dxrx}")

dscCfg = DscConfig("./data", 9999999, 44100)
dscDB = DscDatabases(dscCfg)

msgs = []
with open("/tmp/dsc_test_msgs.txt", 'r') as file:
    for line in file:
        bits = ""
        msgVals = []

        cd = line.strip().split("|")
        cd1 = cd[1]
        csv = cd1[1:-1]
        vals = csv.split(",")
        for v in vals:
            vs = v.strip()
            msgVals.append(int(vs))

        # Test Direct example
        # msgVals = [120, 0, 51, 20, 1, 0, 108, 53, 80, 5, 17, 10, 118, 126, 126, 126, 126, 126, 126, 126, 117, 5]

        if (len(msgVals) > 2):
            seq = dsc_phasing_dxrx + generateDSCMessageSequence(msgVals)
            
            bits = ""
            for v in seq:
                bits += TENunit(v)

            # print(f"BITS: [{bits}]")

            msgs.append(bits)

            # Set up Test FSK Demodulator and DSC Decoder
            bitQ = BitQueue(deque(bits))
            dmf = DSCMessageFactory(bitQ, dscDB)
            msg = dmf.processMessage()

            if msg:
                out = []
                msg.print(out)
                print(f"MSG# {len(msgs)}:")
                print(HLINE)
                for ln in out:
                    print(ln)
            else:
                print(f"MSG# {len(msgs)}: - INVALID - [{msgVals}]")

        # Are we testing a small subset then break:
        if (len(msgVals) < 5):
            break

print(f"Completed processing [{len(msgs)}] test data set(s).")