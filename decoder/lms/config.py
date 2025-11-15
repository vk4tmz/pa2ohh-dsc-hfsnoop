
from util.utils import makedirs
from util.logfile import LogFile

import logging


class LmsConfig:

    log: logging.Logger

    ############################################################################################################################################
    # Configuration
    sampleRate = 44100          # Sample rate of soundcard, 11025 or 44100 preferred
    
    freqRxHz:int                # Used to identify UI and logs
    dataDir:str                 # Root level for Data files
    freqDataDir:str             # Root level for Data files specific to "frequency" (ie running multiple instances)
    audioHistDir:str            # folder location for audio hist recordings
    preserveAudioHistory: bool
    allLog:LogFile              # Log for all messages
    freqBand = 0                # 0, 1, 2, 3 Frequency band
    saX = 200                   # Width of the spectrum screen
    saY = 80                    # Height of the spectrum screen
    saMargin = 10               # Margin left - right for audio buffer and level of spectrum screen
    buttonWidth = 12            # Width of the buttons

    invertTones:bool
    markSym:str = "Y"
    spaceSym:str = "B"

    def __init__(self, dataDir:str, freqRxHz:int, sampleRate:int, invertTones:bool=False, freqBand:int=0, presAudioHist:str="no"):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.dataDir = dataDir
        self.freqRxHz = freqRxHz 
        self.sampleRate = sampleRate
        
        self.invertTones = invertTones

        self.freqDataDir = f"{self.dataDir}/{self.freqRxHz}"
        self.audioHistDir = f"{self.freqDataDir}/audio_hist"
        self.storePreserveAudioHistoryOption(presAudioHist)
        
        # log1
        self.allLog = LogFile("ALL MESSAGES", "selcallAll.txt", f"{self.freqDataDir}/SELCALLall")
        
        self.initializeFolders()
    
    def storePreserveAudioHistoryOption(self, audioHist:str):
        match audioHist.lower():
            case "part":
                self.presAudioHist = PreserveAudioHistory.PARTIAL
            case "full":
                self.presAudioHist = PreserveAudioHistory.FULL
            case "both":
                self.presAudioHist = PreserveAudioHistory.BOTH
            case _:
                self.presAudioHist = PreserveAudioHistory.NO

    def presFullAudioHistory(self) -> bool:
        return (self.presAudioHist in [PreserveAudioHistory.FULL, PreserveAudioHistory.BOTH] )

    def presPartialAudioHistory(self) -> bool:
        return (self.presAudioHist in [PreserveAudioHistory.PARTIAL, PreserveAudioHistory.BOTH] )

    def initializeFolders(self):
        makedirs(self.audioHistDir)
        