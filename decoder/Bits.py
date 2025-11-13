
import logging
import sys

sys.path.insert(0, '..')
sys.path.insert(0, '.')

from collections import deque
from time import sleep
from utils import fromTENunit

WAIT_TIME_FOR_BITS  = 0.025

class BitQueue:
    
    log: logging.Logger
    bits: deque

    def __init__(self, initBits:deque=deque([])) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.bits = initBits
        
    def availableBits(self):
        return len(self.bits)

    def waitForBits(self, minBits:int):
        while len(self.bits) < minBits:
            sleep(WAIT_TIME_FOR_BITS)

    def padBits(self, numBits):
        self.log.debug(f"Pre-padding bit buffer with {numBits} Y's....")
        pad = "Y" * numBits
        self.bits.extendleft(pad)

    def getBits(self, idx:int, length:int) -> str:
        self.waitForBits(idx + length)
    
        res = ""
        for n in range(idx, idx+length):
            res += self.bits[n]

        return res
    
    def removeBits(self, length:int):
        for n in range(0, length):
            self.bits.popleft()

    def append(self, newBits):
        self.bits.append(newBits)

    def length(self):
        return len(self.bits)
    
    def toString(self) -> str:
        return "".join(self.bits)

    # ... Return the value of symbol i (start at 1, only the first 7 bits are used) ...
    def getValSymbol(self, startOfs:int, symIdx:int):

        n = startOfs + (symIdx-1)*10        # msg is start position in strYBY of message
        if n < 0:                           # If out of range of strYBY then return -1
            return(-1)
        
        s = self.getBits(n, 10)

        return fromTENunit(s)