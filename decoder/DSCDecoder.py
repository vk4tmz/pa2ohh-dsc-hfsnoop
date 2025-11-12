import logging
import sys
from time import sleep

sys.path.insert(0, '..')
sys.path.insert(0, '.')

from utils import TENunit, fromTENunit
from audio.source import AudioSource, RawAudioSource
from decoder.FSKDecoder import FSKDecoder, LM_AUTO, LM_MANUAL
from decoder.DSCMessageFactory import DSCMessageFactory

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

class DSCDecoder:

    dec: FSKDecoder
    dscCfg: DscConfig
    dscDB: DscDatabases
    msgFactory: DSCMessageFactory
    log: logging.Logger

    def __init__(self, audioSrc:AudioSource, dscCfg: DscConfig, lockMode:str="A", centerFreq:int=1700, tonesInverted:bool=False):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))

        self.dscDB = DscDatabases(dscCfg)
        self.dec = FSKDecoder(audioSrc=audioSrc, shiftFreq=SHIFTfrequency, bitRate=BITrate, lockMode=lockMode,centerFreq=centerFreq, tonesInverted=tonesInverted)
        self.msgFactory = DSCMessageFactory(dec=self.dec, dscDB=self.dscDB)

    def startDecoder(self):
        # TODO: Thread this
        self.dec.startDecoder()

        while (True):
            self.dec.setLockFreq(False)
            
            print(f"Searching for PhasingDX...",)
            foundPhasing = self.findPhasing()
            if foundPhasing:
                print(f"PhasingDX Found, processing Message")

                # Decode Message
                self.msgFactory.processMessage()

                # Remove bits of at min the Phasing Sequence, to ensure all clear for next Phasing scan.
                self.dec.removeBits(DXRX_PHASING_BIT_LEN+20)
            else:
                print(f"No PhasingDX Found....")


    def logValSymbols(self, startIdx: int):

        if NEW_DEBUG > 1:
            self.log.debug(HLINE)
            self.log.debug("=== DEBUG DATA message ===")
            self.log.debug("Message found at " + str(startIdx))
    
            DATAerror = 0
            strDATA = ""
            i = 1
            while DATAerror < 5:                                    # Print data till 5 errors
                strDATA = strDATA +"(" + str(self.dec.getValSymbol(startIdx, i)) + ")"
                if i > 16:                                          # End of phasing and start of data
                    if self.dec.getValSymbol(startIdx, i) < 0:
                        DATAerror = DATAerror + 1
                i = i + 1

            self.log.debug(strDATA)
            self.log.debug(HLINE)        

    # ============= Find the phasing signal and the start of the message MSG =======================
    def findPhasing(self):

        # ... Find Phasing ...
        MinBits = 30                            # The search bits in the YBY string  30 bits enough to confirm possible (RX, DX, RX )
        Starti = 0                              # Start to search from this pointer, so that the data before this pointer can also be read
            
        # if MSGstatus == 3:                                # Start of new search, skip the old part upto the format specifier
        #     strYBY = strYBY[(MSG+DXRX_PHASING_BIT_LEN):]  # Discard last Phasing Sequence. Ready for next search of phasing signal of 120 bits
        #     FFTaverage = FFTresult                        # Reset FFTaverage for new search
        #     MSGstatus = 0                                 # And set the status to search

        self.dec.waitForBits(MinBits)
                
        # Phasing is [125][111], [125][110] .. [125][105]
        #  Original logic only looked for the match on RX value 108 or 107, which could allow for missed decodes if 
        #  these bytes were corrupted. We should actually look for any Phase [125] plus a value from between 105 and 111. 
        #  
        #   se1 = TENunit(108) + TENunit(125)       # Define search string 1 for phasing
        #   se2 = TENunit(107) + TENunit(125)       # Define search string 2 for phasing
    
        i = Starti
        L = len(self.dec.strYBY)
        while i < L:

            if self.dec.getBits(i, 10) == PHASEDXbits:
                phaseDxIdxBitsA = self.dec.getBits(i+10, 10)     # RX After DX
                phaseDxIdxA = fromTENunit(phaseDxIdxBitsA)
                phaseDxIdxBitsB = self.dec.getBits(i-10, 10)     # RX Before DX
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
                        self.dec.padBits(padLen)
                        phaseDxStartIdx = 0
                        
                    # Ensure we have 120 bits (6xDX + 6xRX) to ensure us to perform out Counts
                    self.dec.waitForBits(phaseDxStartIdx + DXRX_PHASING_BIT_LEN)
                    
                    # Compute Counts of Valid DX and RX values from computed starting DX Phase 
                    phaseDxCnt = 0;
                    phaseRxSeen = [];
                    for phIdx in range(0, 6): # 106..111
                        dxi = phaseDxStartIdx + (phIdx * 20)
                        dxVal = self.dec.getBits(dxi, 10)
                        rxVal = self.dec.getBits(dxi+10, 10)
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
                        self.dec.removeBits(phaseDxStartIdx)

                        # Successfully achieved Phasing.
                        return True
                        

                    # Insufficient Phasing continuing...
                    self.log.debug(f"Insufficient Phasing continuing...")

                    # Clean up - remove any pre-padding
                    if (padLen > 0):
                        self.dec.removeBits(padLen)

            i = i + 1

        # TODO: Migrate this
        # FileHandling()
        
        # Process the processed L BITS up, to clear them out from next Phasing Scan
        self.dec.removeBits(L)
        return None


###########################################################
## Main / Test
###########################################################

def main():
    audioSrc = RawAudioSource(src=sys.stdin.buffer, sampleRate=44100)
    dscCfg = DscConfig(dataDir="./data", freqRxHz=999999, sampleRate=44100)

    #dec = DSCDecoder(audioSrc, lockMode=LM_MANUAL, centerFreq=1700)
    dec = DSCDecoder(audioSrc, dscCfg, lockMode=LM_AUTO)
    dec.startDecoder()

    # print(f"DEBUG: Remaining strYBY - Len: [{len(self.dec.strYBY)}] - Data: [{"".join(self.dec.strYBY)}]")


if __name__ == "__main__":
    main()