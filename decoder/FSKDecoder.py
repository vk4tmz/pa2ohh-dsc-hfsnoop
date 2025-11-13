
import logging
import math
import numpy
import sys
import threading

sys.path.insert(0, '..')
sys.path.insert(0, '.')

from utils import TENunit, fromTENunit
from audio.source import AudioSource, RawAudioSource
from decoder.Bits import BitQueue
from collections import deque
from time import sleep

MAX_AUDIO_BUFFER_SIZE = 44100 * 30; 
LM_AUTO = "A"
LM_MANUAL = "M"

WAIT_TIME_FOR_AUDIO = 0.02

############################################################################################################################################
# Initialisation of global variables required in various routines (MODIFY THEM ONLY IF NECESSARY!)
SYNCTfactor = 0.02          # Correction factor for time synchronisation
SYNCTfactorLocked = 0.01    # Correction factor for time synchronisation if phasing found
SYNCFfactor = 0.03          # Average factor for frequency synchronisation curve average
FFTwindow = False           # [DEFAULT=False] FFTwindow applied if True
ZEROpadding = 4             # [DEFAULT=4] Zero padding for extra FFT points

class FSKDecoder:
    log: logging.Logger

    audioSrc: AudioSource
    audioSignalA:deque
    audioSignal1:deque
    audioHandlerRunning:bool = False
    audioHandlerThread:threading.Thread

    decoderHandlerRunning:bool = False
    decoderHandlerThread:threading.Thread

    strYBY: BitQueue 
    markSym: str = "Y"
    spaceSym: str = "B"

    shiftFreq: int = 170
    bitRate: float = 100
    bitStep:float = 0.0
    bitStepFrac:float = 0.0

    fftResult = []
    fftAverage = []
    fftLength:int = 0
    lowSearchf:int = 400
    highSearchf:int = 2400

    startSample:int = 0
    stopSample:int = 0
    shiftSamples:int = 0

    syncTcor = 0                # Correction for time synchronisation in samples
    syncTmin = 1.0              # Minimum correction value RESET TO +1.0                       
    syncTmax = -1.0             # Maximum correction value RESET TO -1.0
    syncTcntplus = 0            # Number of plus counts time synchronization
    syncTcntminus = 0           # Number of minus counts time synchronization
    syncTVold1 = 0.0            # The old value1
    syncTVold2 = 0.0            # The old value2

    bitOld = "Y"                # The previous bit
    bitNew = "B"                # The new bit 

    lck_mode = LM_AUTO          # "M"anual  or "A"uto
    lck_centerFreq = 1700
    isLockFreq: bool = False    # Used by external decoder (ie DSCDecoder to let fsk know to lock/unlock centre freq)
    tonesInverted: bool = False

    framecnt=0

    def __init__(self, audioSrc:AudioSource, shiftFreq: int, bitRate: float, lockMode:str="A", centerFreq:int=1700, tonesInverted:bool=False):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.audioSrc = audioSrc
        self.shiftFreq = shiftFreq
        self.bitRate = bitRate
        self.lck_mode = lockMode
        self.lck_centerFreq = centerFreq
        self.tonesInverted = tonesInverted

        self.strYBY = BitQueue()
        self.updateFFTParams(400, 2400)

    def invertTonesBits(self):
        if self.tonesInverted:
            tmp = self.bitY
            self.bitY = self.bitB
            self.bitB = tmp

    def updateFFTParams(self, lowSearchf:int, highSearchf:int):
        self.lowSearchf = lowSearchf
        self.highSearchf = highSearchf

        sampleRate = self.audioSrc.sampleRate

        self.bitStep = sampleRate / self.bitRate
        self.fftLength = 2**int(math.log2(self.bitStep * ZEROpadding) + 0.5)
        
        self.startSample = int(float(self.lowSearchf) / (sampleRate / (self.fftLength - 1)) + 0.5)
        self.stopSample = int(float(self.highSearchf) / (sampleRate / (self.fftLength - 1)) + 0.5)
        self.shiftSamples = int(float(self.shiftFreq) / (sampleRate / (self.fftLength - 1)) + 0.5)
        # print(f"DEBUG: startSample: [{self.startSample}], stopSample: [{self.stopSample}], shiftSamples: [{self.shiftSamples}]")

        # TODO: Review new "invert tones" switch to see if this needs updating 
        if (self.lck_mode == LM_AUTO):
            self.bitY = int(((self.lowSearchf + self.highSearchf - self.shiftFreq) / 2) / (sampleRate / (self.fftLength - 1)) - self.startSample + 0.5)
            self.bitB = self.bitY + self.shiftSamples
        else:
            self.bitY = int((self.lck_centerFreq - (self.shiftFreq / 2)) / (sampleRate / (self.fftLength - 1)) - self.startSample + 0.5)
            self.bitB = self.bitY + self.shiftSamples

        self.invertTonesBits()
        

    ########################################################################################################
    # Audio Handler
    ########################################################################################################

    def audioHandler(self):
        # TODO: remove audioSignal1 init, was added to allow logging of both Q's here
        self.audioSignal1 = deque([], MAX_AUDIO_BUFFER_SIZE)
        self.audioSignalA = deque([])

        while (self.audioHandlerRunning):

            buffervalue = self.audioSrc.available()           # Buffer reading testroutine
            try:
                data = self.audioSrc.read(buffervalue)                    
                self.audioSignalA.append(data)
                # print(f"DEBUG: Audio Len: A: [{len(self.audioSignalA)}],  1: [{len(self.audioSignal1)}]")
            except Exception as e:
                self.log.error(f"Audio buffer reset! {e}")

            sleep(WAIT_TIME_FOR_AUDIO)

    def openAudioSource(self):
            try:
                self.audioSrc.open()
            except Exception as e:
                raise Exception(f"Cannot open Audio Stream Sample rate: [{self.audioSrc.sampleRate} not supported. {e}])") from e


    def startAudioHandler(self):
        self.openAudioSource();
        self.audioHandlerThread = threading.Thread(target=self.audioHandler, args=(), daemon=True)
        self.audioHandlerRunning = True
        self.audioHandlerThread.start()
    
    def stopAudioHandler(self):
        self.audioHandlerRunning = False
        self.audioHandlerThread.join(2.0)   # wait for the audio thread to complete
        self.audioSrc.close()

    ########################################################################################################
    # Decoder Handler
    ########################################################################################################

    def decoderHandler(self):
        self.audioSignal1 = deque([])
        while (self.decoderHandlerRunning):
            self.MakeYBY()


    def startDecoder(self):
        self.startAudioHandler();
        
        self.decoderHandlerThread = threading.Thread(target=self.decoderHandler, args=(), daemon=True)
        self.decoderHandlerRunning = True
        self.decoderHandlerThread.start()

    def stopDecoder(self):
        self.stopAudioHandler();

        self.decoderHandlerRunning = False
        self.decoderHandlerThread.join(2.0)   # wait for the audio thread to complete
    

    # ============= Do an FFT =======================
    def DoFFT(self, FROMsample, Length):                              # Fast Fourier transformation and others like noise blanker and level for audio meter and time markers
        #print(f"DEBUG: DoFFT() - FROMsample: [{FROMsample}], Length: [{Length}]")
        # Correction for Bandwidth of FFT window as samples left and right are suppressed by the window
        if FFTwindow:
            CF = 2.5                                            # Correction factor for Bandwidth of FFT window
            FROMsample = int(FROMsample - (Length * (CF - 1) / 2) + 0.5)
            Length = int(Length * CF + 0.5)
            
        # print(f"DEBUG: B - {len(self.audioSignal1)}, FROMsample: [{FROMsample}], Length: [{Length}]")
        while len(self.audioSignal1) <= (FROMsample + Length + 1):   # If buffer too small, call the audio read routine
            if (len(self.audioSignalA) > 0):
                self.audioSignal1.extend(self.audioSignalA.popleft())
            else:
                sleep(WAIT_TIME_FOR_AUDIO)                                         # Reduces processing power in loop

        fftSignal = [0] * Length;
        fsi = 0;
        for n in range(FROMsample, FROMsample+Length):              # Take the Length samples from the stream
            fftSignal[fsi] = self.audioSignal1[n]
            fsi += 1

        # print(f"DEBUG: audioSignal1 - [{len(self.audioSignal1)}]  fftSignal: [{len(fftSignal)}]")

        # Convert list to numpy array REX for faster Numpy calculations
        REX = numpy.array(fftSignal)                            # Make an array of the list

        # Do the FFT window function if FFTwindow == True
        if FFTwindow:
            W = numpy.kaiser(len(fftSignal),8)                  # The Kaiser window with B=8 shape
            REX = REX * W                         

        # FFT with numpy 
        fftResult = numpy.fft.fft(REX, n=self.fftLength)             # Do FFT+zeropadding till n=FFTlength with NUMPY
                                                                # FFTresult = Real + Imaginary part
        fftResult = fftResult[self.startSample:self.stopSample]           # Delete the unused samples
        fftResult = numpy.absolute(fftResult)                   # Make absolute SQR(REX*REX + IMX*IMX) for VOLTAGE!

        return fftResult


    # ============= Time synchronisation =======================
    def SyncTime(self):
        
        if not self.isLockFreq:             # Not locked, do a FFT with start halfway bitstep
            SF = SYNCTfactor
            EXTRA = 1.0                     # NO extra long FFT array
        else:                               # Locked
            SF = SYNCTfactorLocked
            EXTRA = 1.5                     # A little experimental extra length when locked

        Length = int(EXTRA * self.bitStep + 0.5)
        Start = int(5 * self.bitStep - EXTRA * self.bitStep / 2)
        self.fftResult = self.DoFFT(Start, Length)                # Do a FFT start halfway both bits

        VB = self.fftResult[self.bitB]
        VY = self.fftResult[self.bitY]

        if self.bitNew == "Y":
            V1 = VB + self.syncTVold1
            V2 = VY + self.syncTVold2
            self.syncTVold1 = VB
            self.syncTVold2 = VY
        else: # if "B"
            V1 = VY + self.syncTVold1
            V2 = VB + self.syncTVold2
            self.syncTVold1 = VY
            self.syncTVold2 = VB

        self.syncTcor = int(SF * self.bitStep + 0.5)
        if V1 < V2:                                    # Zero crossing has to be correcter later instead of earlier
            self.syncTcor = -1 * self.syncTcor

        if self.syncTcor >= 0:                         # Count the plus and minus corrections for the display
            self.syncTcntplus = self.syncTcntplus + 1
        else:
            self.syncTcntminus = self.syncTcntminus + 1
            
        # print(f"DEBUG:  syncTcor: [{self.syncTcor}], syncTcntplus: [{self.syncTcntplus}], syncTcntminus: [{self.syncTcntminus}]")

        try:
            V = (VB - VY) / (VB + VY)
        except:
            V = 0.0         # Solve division by zero errors

        if V > self.syncTmax:    # For the display, orange sync line
            self.syncTmax = V
        if V < self.syncTmin:
            self.syncTmin = V

    # ============= Frequency synchronisation =======================
    def SyncFreq(self):

        if len(self.fftAverage) != len(self.fftResult):
            self.fftAverage = self.fftResult
            return

        self.fftAverage = (1 - SYNCFfactor) * numpy.maximum(self.fftResult, self.fftAverage)   # The peak, fast attack, slow decay
        # FFTaverage = FFTaverage + SYNCFfactor * (FFTresult - FFTaverage)       # Average not used, fast attack is better

        if (self.lck_mode == LM_MANUAL) or self.isLockFreq:          # Only continue if (find phasing)
            return
    
        B = numpy.argmax(self.fftAverage)                            # Find the sample number with the maximum

        if B < self.shiftSamples:
            self.bitY = B
            self.bitB = B + self.shiftSamples
            return

        if B >= len(self.fftAverage) - self.shiftSamples:
            self.bitB = B
            self.bitY = B - self.shiftSamples
            return

        if self.fftAverage[B-self.shiftSamples] < self.fftAverage[B+self.shiftSamples]:
            self.bitY = B
            self.bitB = B + self.shiftSamples
        else:
            self.bitB = B
            self.bitY = B - self.shiftSamples

        self.invertTonesBits()
    
    # ============= Convert AUDIOsignal1[] audio data to strYBY =======================
    def MakeYBY(self):                              # Read the audio and make strYBY

        AddYBY = 0                                  # Counts the number of YBY's that have been added
        while AddYBY < 50:                          # Add xx YBY's 
            # print(f"{self.framecnt:05d}: ", end='')
            self.framecnt += 1
            self.fftResult = self.DoFFT(int(5 * self.bitStep), int(self.bitStep))   # Do a FFT start at 5*BitStep for extra buffer

            # NIET: V = FFTresult[BitY] - FFTresult[BitB] - (Yref - Bref) / 2
            V = self.fftResult[self.bitY] - self.fftResult[self.bitB]
            # print(f"DEBUG: V: [{V}],  bitY: [{self.fftResult[self.bitY]}], bitB: [{self.fftResult[self.bitB]}]")
            if (V > 0):
                self.strYBY.append(self.markSym)               # Add "Y" for  1 for low tone
                self.bitNew = self.markSym
            else:
                self.strYBY.append(self.spaceSym)              # Add "B" for 0 for high tone
                self.bitNew = self.spaceSym
                
            self.SyncFreq()

            if self.bitNew != self.bitOld:
                self.SyncTime()

            # print(f"DEBUG: bitOld: [{self.bitOld}], bitNew: [{self.bitNew}] - BitY: [{self.bitY}]  BitB: [{self.bitB}]")
            self.bitOld = self.bitNew

            self.bitStepFrac = self.bitStepFrac + self.bitStep - int(self.bitStep)               # Fractional counter
            purgeNBits = int(self.bitStep + int(self.bitStepFrac) + self.syncTcor)
            #print(f"DEBUG: purging [{purgeNBits}] Bits - ({self.bitStep, int(self.bitStepFrac)}, {self.syncTcor})")
            l1 = len(self.audioSignal1)
            for n in range(0, purgeNBits):        # Delete the samples of a bit
                self.audioSignal1.popleft()
            l2 = len(self.audioSignal1)
            # print(f"DEBUG: Audio Lens BP: [{l1}] AP: [{l2})]")
            self.bitStepFrac = self.bitStepFrac - int(self.bitStepFrac)                          # Only fractional part
            self.syncTcor = 0                                                                    # Reset SYNCTcor

            AddYBY = AddYBY + 1
    
    def setLockFreq(self, isLocked:bool):
        self.isLockFreq = isLocked

###########################################################
## Main / Test
###########################################################

def main():
    audioSrc = RawAudioSource(src=sys.stdin.buffer, sampleRate=44100)

    # dec = FSKDecoder(audioSrc, 170, 100, lockMode=LM_MANUAL, centerFreq=1700)
    # dec = FSKDecoder(audioSrc, 170, 100, lockMode=LM_AUTO)

    # strange SigId Example GDMSS_2.mp3 - inverted
    dec = FSKDecoder(audioSrc, 170, 100, lockMode=LM_AUTO, tonesInverted=True)
    # dec = FSKDecoder(audioSrc, 170, 100, lockMode=LM_MANUAL, centerFreq=1700, tonesInverted=True)

    # SELCALL 
    # dec = FSKDecoder(audioSrc, 170, 100, lockMode=LM_AUTO, tonesInverted=True)
    # dec = FSKDecoder(audioSrc, 170, 100, lockMode=LM_MANUAL, centerFreq=1800, tonesInverted=True)

    dec.startDecoder()

    cnt = 0
    ps = -1;
    while (cnt < 600):
        sleep(0.1)
        if dec.strYBY.length() > ps:
            ps = dec.strYBY.length()
        else:
            # buffer has not grown so assume end of processing reached
            break

        cnt += 1

    print(f"DEBUG: strYBY - Len: [{dec.strYBY.length()}] - Data: [{dec.strYBY.toString()}]")
    dec.stopDecoder()


if __name__ == "__main__":
    main()