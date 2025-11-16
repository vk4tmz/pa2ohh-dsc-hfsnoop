
from decoder.config import Config
from util.utils import makedirs
from util.logfile import LogFile

import logging


class LmsConfig(Config):

    log: logging.Logger

    ############################################################################################################################################
    # Configuration
    allLog:LogFile              # Log for all messages
    

    def __init__(self, dataDir:str, freqRxHz:int, sampleRate:int, invertTones:bool=False, freqBand:int=0, presAudioHist:str="no"):
        super().__init__(dataDir, freqRxHz, sampleRate, invertTones, freqBand, presAudioHist)
        pass
    
    def setupConfig(self):
        super().setupConfig()

        # log1
        self.allLog = LogFile("ALL MESSAGES", "lmsAll.txt", f"{self.freqDataDir}/LMSall")
        

    def initializeFolders(self):
        super().initializeFolders()
        pass
        