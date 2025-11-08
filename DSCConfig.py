
from utils import makedirs

import pandas as pd


class LogFile:
    title:str
    filename:str
    dirname:str

    def __init__(self, title:str, filename:str, dirname: str):
        self.title=title
        self.filename=filename
        self.dirname=dirname
        makedirs(dirname);
    
    def getFullPath(self):
        return f"{self.dirname}/{self.filename}"


class DscConfig:

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
    mids:list                   # Lookup list by MID for Country

    def __init__(self, dataDir:str, freqRxHz:int, sampleRate:int):
        self.dataDir = dataDir
        self.freqRxHz = freqRxHz 
        self.sampleRate = sampleRate
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
        self.loadMids()
    

    def initializeFolders(self):
        makedirs(self.dirDay);
        makedirs(self.dirCoast);
        makedirs(self.dirShip);
        makedirs(self.dirPos);

    def loadMids(self):
        # MIDs (Maritime Identification Digits) sourced from "https://www.itu.int/gladapp/Allocation/MIDs"
        #    The first three digits of the MMSI are known as the Maritime Identification Digits (MID). 
        #    The MID represents the country of registration of the vessel, or the country in which the DSC shore station 
        #    is located.
        #
        #  - To refresh - Download "xlsx" and convert to CSV

        self.mids = []
        for n in range(0, 1001):
            self.mids.append("Unkown")

        df = pd.read_csv(self.midsFilename)

        for index, row in df.iterrows():
            self.mids[row['Digit']] = row['Allocated to']
