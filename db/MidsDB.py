
import logging
import time

from DSCConfig import DscConfig
import pandas as pd

class MidsDB:

    log: logging.Logger

    dscCfg:DscConfig
    mids:list                   # Lookup list by MID for Country

    def __init__(self, dscCfg:DscConfig):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.dscCfg = dscCfg

        self.loadMids()

    def lookup(self, id:int):        
        if (0 < id >= 1000):
            return "Unknown"
        
        return self.mids[id]

    def loadMids(self):
        # MIDs (Maritime Identification Digits) sourced from "https://www.itu.int/gladapp/Allocation/MIDs"
        #
        #    The first three digits of the MMSI are known as the Maritime Identification Digits (MID). 
        #    The MID represents the country of registration of the vessel, or the country in which the DSC shore station 
        #    is located.
        #
        #  - To refresh - Download "xlsx" and convert to CSV

        self.mids = []
        for n in range(0, 1001):
            self.mids.append("Unkown")

        df = pd.read_csv(self.dscCfg.midsFilename)

        row=0
        try:
            for index, row in df.iterrows():
                self.mids[row['Digit']] = row['Allocated to']
        except:
            self.log.error(f"MIDS database error line: {row}")
        
