import logging
import sys
import threading

sys.path.insert(0, '..')
sys.path.insert(0, '.')


from enum import Enum
from pyventus.events import AsyncIOEventEmitter, EventEmitter, EventLinker
from utils import TENunit, fromTENunit

from audio.source import AudioSource, RawAudioSource
from decoder.Bits import BitQueue
from decoder.FSKDecoder import FSKDecoder, LM_AUTO, LM_MANUAL
from decoder.DSCMessageFactory import DSCMessageFactory
from decoder.DSCEvents import NewDscMessageEvent, LogDscInfoEvent, LogDscResultEvent

from DSCConfig import DscConfig
from db.DSCDatabases import DscDatabases


SHIFTfrequency = 170        # 170 for MF - HF
BITrate = 100.0             # Bitrate 100 for MF - HF

FORMAT_SPECIFIERS = [102, 112, 114, 116, 120, 123]  # 
FORMAT_SPECIFIERS_SAME = [112, 116]                 # Distress and All Ships 
DXRX_PHASING_BIT_LEN = 120                          # (6xDX + 6xRX)x10
PHASEDXbits = TENunit(125)

NEW_DEBUG = 0
HLINE = "==================================="       # Message separation line

logging.basicConfig(level=logging.DEBUG)


@EventLinker.on(NewDscMessageEvent)
def printNewMessage(e:NewDscMessageEvent):
    out = []
    e.msg.print(out)
    print(HLINE)
    for ln in out:
        print(ln)


class DSCDecoder:

    dec: FSKDecoder
    bits: BitQueue
    dscCfg: DscConfig
    dscDB: DscDatabases
    msgFactory: DSCMessageFactory

    log: logging.Logger
    debugLevel = 0;

    decoderHandlerRunning: bool = False
    decoderHandlerThread:threading.Thread

    _event_emitter:EventEmitter

    def __init__(self, audioSrc:AudioSource, dscCfg: DscConfig, lockMode:str="A", centerFreq:int=1700, tonesInverted:bool=False):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))

        self.dscDB = DscDatabases(dscCfg)
        self.dec = FSKDecoder(audioSrc=audioSrc, shiftFreq=SHIFTfrequency, bitRate=BITrate, lockMode=lockMode,centerFreq=centerFreq, tonesInverted=tonesInverted)
        self.bits = self.dec.strYBY
        self.msgFactory = DSCMessageFactory(bits=self.dec.strYBY, dscDB=self.dscDB)
        self._event_emitter = AsyncIOEventEmitter()

    def setDebugLevel(self, dbgLvl:int):
        self.debugLevel = dbgLvl
        self.dec.setDebugLevel(dbgLvl)

    def setFreqBand(self, lowSearchf, highSearchf):
        self.dec.setFreqBand(lowSearchf, highSearchf)

    def startDecoder(self):
        self.decoderHandlerThread = threading.Thread(target=self.decoderHandler, args=(True,), daemon=True)
        self.decoderHandlerThread.start()

    def stopDecoder(self):
        self.decoderHandlerRunning = False
        self.decoderHandlerThread.join(2.0)   # wait for the audio thread to complete

    def notifyLogInfo(self, txt:str):
        e = LogDscInfoEvent(txt=txt)
        self._event_emitter.emit(e)

    def notifyLogResults(self, txt:str):
        e = LogDscResultEvent(txt=txt)
        self._event_emitter.emit(e)

    def debugMessageData(self):
        if self.debugLevel > 1:
            txt = f"{HLINE}\n"
            txt += f"=== DEBUG DATA message ===\n"
            txt += f"Message found: \n"
    
            errCnt = 0
            msgVals = ""
            i = 1
            while errCnt < 5:                                    # Print data till 5 errors
                v = self.bits.getValSymbol(0, i)                      
                msgVals += f"({v})"
                if i >= 16:                                         # End of phasing and start of data
                    if v < 0:
                        errCnt = errCnt + 1
                i = i + 1

            txt += msgVals
            self.notifyLogResults(txt)


    def decoderHandler(self, startRunning:bool):
        
        if (self.decoderHandlerRunning):
            self.log.warning("DSCDecoder process is already running...")

        self.decoderHandlerRunning = startRunning

        self.dec.startDecoder()
        try:
            while (self.decoderHandlerRunning):
                self.dec.setLockFreq(False)
                
                self.log.debug(f"Searching for PhasingDX...",)
                foundPhasing = self.findPhasing()
                if foundPhasing:
                    try:
                        self.log.debug(f"PhasingDX Found, processing Message")

                        print(f"Bits Before: {self.bits.length()}")
                        self.debugMessageData()
                        print(f"Bits After: {self.bits.length()}")

                        # Decode Message
                        msg = self.msgFactory.processMessage()

                        if msg:
                            e = NewDscMessageEvent(msg=msg)
                            self._event_emitter.emit(e)

                    finally:
                        # Remove bits of at min the Phasing Sequence, to ensure all clear for next Phasing scan.
                        self.bits.removeBits(DXRX_PHASING_BIT_LEN+20)
                else:
                    self.log.debug(f"No PhasingDX Found....")
        finally:
            self.dec.stopDecoder()


    def logValSymbols(self, startIdx: int):

        if NEW_DEBUG > 1:
            self.log.debug(HLINE)
            self.log.debug("=== DEBUG DATA message ===")
            self.log.debug("Message found at " + str(startIdx))
    
            DATAerror = 0
            strDATA = ""
            i = 1
            while DATAerror < 5:                                    # Print data till 5 errors
                strDATA = strDATA +"(" + str(self.bits.getValSymbol(startIdx, i)) + ")"
                if i > 16:                                          # End of phasing and start of data
                    if self.bits.getValSymbol(startIdx, i) < 0:
                        DATAerror = DATAerror + 1
                i = i + 1

            self.log.debug(strDATA)
            self.log.debug(HLINE)        
    

    # ============= Find the phasing signal and the start of the message MSG =======================
    def findPhasing(self):

        # ... Find Phasing ...
        MinBits = 30                            # The search bits in the YBY string  30 bits enough to confirm possible (RX, DX, RX )
        Starti = 0                              # Start to search from this pointer, so that the data before this pointer can also be read
            
        self.bits.waitForBits(MinBits)
                
        # Phasing is [125][111], [125][110] .. [125][105]
        #  Original logic only looked for the match on RX value 108 or 107, which could allow for missed decodes if 
        #  these bytes were corrupted. We should actually look for any Phase [125] plus a value from between 105 and 111.
    
        i = Starti
        L = self.bits.length()
        while i < L:

            if self.bits.getBits(i, 10) == PHASEDXbits:
                phaseDxIdxBitsA = self.bits.getBits(i+10, 10)     # RX After DX
                phaseDxIdxA = fromTENunit(phaseDxIdxBitsA)
                phaseDxIdxBitsB = self.bits.getBits(i-10, 10)     # RX Before DX
                phaseDxIdxB = fromTENunit(phaseDxIdxBitsB)
                
                foundPossiblePhasing = False
                if (phaseDxIdxA >= 106) and (phaseDxIdxA <= 111):
                    phaseDxStartIdx = i - (111-phaseDxIdxA) * 20
                    foundPossiblePhasing = True
                elif (phaseDxIdxB >= 106) and (phaseDxIdxB <= 111):
                    phaseDxStartIdx = i - ((111-phaseDxIdxB+1) * 20)
                    foundPossiblePhasing = True
                
                if (foundPossiblePhasing):
                    
                    self.dec.setLockFreq(True)

                    # Check if we need to prepad strYBY so Computed MSG starts at a first DX Phasing sequence
                    padLen = 0
                    if (phaseDxStartIdx < 0):
                        padLen = abs(phaseDxStartIdx)
                        self.bits.padBits(padLen)
                        phaseDxStartIdx = 0
                        
                    # Ensure we have 120 bits (6xDX + 6xRX) to ensure us to perform out Counts
                    self.bits.waitForBits(phaseDxStartIdx + DXRX_PHASING_BIT_LEN)
                    
                    # Compute Counts of Valid DX and RX values from computed starting DX Phase 
                    phaseDxCnt = 0;
                    phaseRxSeen = [];
                    for phIdx in range(0, 6): # 106..111
                        dxi = phaseDxStartIdx + (phIdx * 20)
                        dxVal = self.bits.getBits(dxi, 10)
                        rxVal = self.bits.getBits(dxi+10, 10)
                        if dxVal == PHASEDXbits:
                            phaseDxCnt += 1
                        if rxVal == TENunit(111-phIdx):
                            phaseRxSeen.append(111-phIdx)

                    self.log.debug(f"PhaseDXfound: {i} - DXCnt: [{phaseDxCnt}]  RXSeen: [{phaseRxSeen}]")

                    # ITU DSC Spec: 
                    #   3.3 Phasing is considered to be achieved when two DXs and one RX, or two RXs and one DX,
                    #   or three RXs in the appropriate DX or RX positions, respectively, are successfully received. These
                    #   three phasing characters may be detected in either consecutive or non-consecutive positions but in
                    #   both cases all bits of the phasing sequence should be examined for a correct 3-character pattern.
                    #   A call should be rejected only if a correct pattern is not found anywhere within the phasing
                    #   sequence.

                    if (((phaseDxCnt >= 2) and (len(phaseRxSeen) >= 1)) or
                        ((phaseDxCnt >= 1) and (len(phaseRxSeen) >= 2)) or
                        (len(phaseRxSeen) >= 3)):

                        self.logValSymbols(phaseDxStartIdx)

                        # Remove all bits prior to start of First PhasingDX
                        self.bits.removeBits(phaseDxStartIdx)

                        # Successfully achieved Phasing.
                        return True
                        

                    # Insufficient Phasing continuing...
                    self.log.debug(f"Insufficient Phasing continuing...")

                    # Clean up - remove any pre-padding
                    if (padLen > 0):
                        self.bits.removeBits(padLen)

            i = i + 1
        
        # Process the processed L BITS up, to clear them out from next Phasing Scan
        self.bits.removeBits(L)
        return None


###########################################################
## Main / Test
###########################################################

def main():
    audioSrc = RawAudioSource(src=sys.stdin.buffer, sampleRate=44100)
    dscCfg = DscConfig(dataDir="./data", freqRxHz=999999, sampleRate=44100)

    #dec = DSCDecoder(audioSrc, lockMode=LM_MANUAL, centerFreq=1700)
    dec = DSCDecoder(audioSrc, dscCfg, lockMode=LM_AUTO)

    # GMDSS_2 - Is Inverted
    # dec = DSCDecoder(audioSrc, dscCfg, lockMode=LM_AUTO, tonesInverted=True)
    
    dec.startDecoder()
    dec.decoderHandlerThread.join()

    # print(f"DEBUG: Remaining strYBY - Len: [{len(self.dec.strYBY)}] - Data: [{"".join(self.dec.strYBY)}]")


if __name__ == "__main__":
    main()