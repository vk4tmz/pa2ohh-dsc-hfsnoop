
from utils import makedirs
from logfile import LogFile

import logging

class DscConfig:

    log: logging.Logger

    ############################################################################################################################################
    # Configuration
    dbCoast = 2                 # Database Coast: 0=none; 1=MultiPSK; 2=YADD
    dbShip = 2                  # Database Ship: 0=none; 1=MultiPSK; 2=YADD
    sampleRate = 44100          # Sample rate of soundcard, 11025 or 44100 preferred
    
    freqRxHz:int                # Used to identify UI and logs
    dataDir:str                 # Root level for Data files
    freqDataDir:str             # Root level for Data files specific to "frequency" (ie running multiple instances)
    dscAllLog:LogFile           # Log for all messages
    dscMinusTestLog:LogFile     # Log for messages except test messages
    dscSpecialMsgLog:LogFile    # Log for special messages like for example Distress or a special MMSI

    dirDay:str                  # Directory for the daily files
    dirCoast:str                # Directory for the mmsi coast station files
    dirShip:str                 # Directory for the mmsi ship station files
    dirPos:str                  # Directory for the ship position files

    ftpTime = 30                # FTP interval time in minutes, integer of 60!!!
    ftpFilename:str

    dayOfMonth = False          # If False, Day Of Week is selected for Day Name (0=Sunday) instead of Day Of Month
    freqBand = 0                # 0, 1, 2, 3 Frequency band
    saX = 200                   # Width of the spectrum screen
    saY = 80                    # Height of the spectrum screen
    saMargin = 10               # Margin left - right for audio buffer and level of spectrum screen
    buttonWidth = 12            # Width of the buttons

    midsFilename:str            # File contain CSV ofs MMSI (MID and AllocatedTo) data

    invertTones:bool
    markSym:str = "Y"
    spaceSym:str = "B"

    multiPSKCoastDB_fn = "./MultiPSKcoast.txt"
    multiPSKShipDB_fn = "./MultiPSKship.txt"

    yaddCoastDB_fn = "./YADDcoast.txt"
    yaddShipDB_fn = "./YADDship.txt"

    ensureFormatSpecifiersSame:bool = False  # ITU Spec - 4.2 Specifiers (112, 116 & 114) should have the value for both Format Specifier message fields.

    def __init__(self, dataDir:str, freqRxHz:int, sampleRate:int, invertTones:bool=False, freqBand:int=0):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.dataDir = dataDir
        self.freqRxHz = freqRxHz 
        self.sampleRate = sampleRate
        self.invertTones = invertTones
        self.freqBand = freqBand

        self.freqDataDir = f"{self.dataDir}/{self.freqRxHz}"
        
        # log1
        self.dscAllLog = LogFile("DSC ALL MESSAGES", "dscall.txt", f"{self.freqDataDir}/DSCall")
        # log2
        self.dscMinusTestLog = LogFile("DSC WITHOUT TEST MESSAGES", "dscminustest.txt", f"{self.freqDataDir}/DSCminustest/")
        # log3
        self.dscSpecialMsgLog = LogFile("DSC SPECIAL MESSAGES", "dscspecial.txt", f"{self.freqDataDir}/DSCspecial/")
    
        self.dirDay = f"{self.freqDataDir}/DSCday/"       # Directory for the daily files
        self.dirCoast = f"{self.freqDataDir}/DSCcoast/"   # Directory for the mmsi coast station files
        self.dirShip =  f"{self.freqDataDir}/DSCship/"    # Directory for the mmsi ship station files
        self.dirPos =  f"{self.freqDataDir}/DSCpos/"      # Directory for the ship position files
        
        self.ftpFilename = f"{self.freqDataDir}/FTPuploads.txt"
        self.midsFilename = f"./mmsi_mids.csv"

        self.initializeFolders()
    

    def initializeFolders(self):
        makedirs(self.dirDay);
        makedirs(self.dirCoast);
        makedirs(self.dirShip);
        makedirs(self.dirPos);
