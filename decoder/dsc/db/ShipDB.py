
import logging
import time

from decoder.dsc.config import DscConfig
from util.utils import getTimeStamp

class ShipDB:

    log: logging.Logger

    dscCfg:DscConfig

    SHIPmmsi = []
    SHIPinfo = []

    def __init__(self, dscCfg:DscConfig):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.dscCfg = dscCfg

        if self.dscCfg.dbShip == 1:
            self.fillMultiPSKship()  # Load the MultiPSKship data base
        elif self.dscCfg.dbShip == 2:
            self.fillYADDship()      # Load the YADDship data base
        else:
            raise Exception(f"Invalid ShipDB Type: [{self.dscCfg.dbShip}]")



    # ... Check Ship data base and save the files ... 
    def lookup(self, MMSI, Country, AlwaysSave) -> int:
        # Always save if AlwaysSave == True, if False only if there is a match

        n = 0
        SHIPindex = -1     # No valid value
        m = int(MMSI)
        while n < len(self.SHIPmmsi):
            mm =  int(self.SHIPmmsi[n])
            if m == mm:
                SHIPindex = n
                break
            n = n + 1
        
        if AlwaysSave == False and SHIPindex == -1: # No save if no match 
            return SHIPindex
        
        self.updateShipStats(SHIPindex, MMSI, Country)
        
        return SHIPindex

    def updateShipStats(self, SHIPindex, MMSI, Country):
        MM = []
        n = 0
        while n < 12:
            MM.append(0)
            n = n + 1

        try:
            filename = f"{self.dscCfg.dirShip}/{MMSI}.txt"
            Rfile = open(filename,'r')          # Input file
            txt = Rfile.readline()              # read the first info line
            n = 0
            while n < 12:
                txt = Rfile.readline()          # read 12 month values
                MM[n] = int(txt)
                n = n + 1
            Rfile.close()
        except:
            pass 

        DT = time.gmtime()

        TheMonth = time.strftime("%m", DT)      # The FileDay of the Month
        M = int(TheMonth) - 1                   # Convert to 0 - 11
        MM[M] = MM[M] + 1

        Wfile = open(filename,'w')
        txt = MMSI + "  " + getTimeStamp()          # Write first line
        Wfile.write(txt + "\n")

        n = 0
        while n < 12:
            txt = str(MM[n])                    # Write 12 month values
            Wfile.write(txt + "\n")
            n = n + 1

        if SHIPindex == -1:
            Wfile.write(Country + "\n")
            Wfile.write("No information" + "\n")
        else:
            Wfile.write(Country + "\n")
            Wfile.write(self.SHIPinfo[SHIPindex] + "\n")
        Wfile.close()


    # ... Fill the YADD ship data base ...
    def fillYADDship(self):

        filename = self.dscCfg.yaddShipDB_fn

        self.SHIPmmsi = []
        self.SHIPinfo = []

        try:
            Rfile = open(filename,'r', encoding='utf-8', errors='ignore') # Input file
            # Rfile = open(filename,'r') # Input file
        except:
            self.log.error(f"No SHIP database [{filename}]")
            return
            
        line = 0  
        while(True):
            line = line + 1
            txt = Rfile.readline()          # Read the next line
            if txt == "":                   # Till empty = end
                Rfile.close()               # Close the file
                break                       # And exit the while loop

            try:
                Vmmsi = txt[0:9]
                s = int(Vmmsi)              # Check for integer number

                Vinfo = txt[10:-1]          # -1 to delete the LF or CR    

                self.SHIPmmsi.append(Vmmsi)
                self.SHIPinfo.append(Vinfo)
                # print("["+Vmmsi+"]["+Vinfo+"]")
            except:
                self.log.error(f"SHIP database error line: {line}")
            
        Rfile.close()                       # Close the file

        self.log.info(f"{filename} database inputs: {len(self.SHIPmmsi)}")


    # ... Fill the MuliPSK ship data base ...
    def fillMultiPSKship(self):
    
        filename = self.dscCfg.multiPSKShipDB_fn

        try:
            # Rfile = open(filename,'r', encoding='utf-8', errors='ignore') # Input file
            Rfile = open(filename,'r') # Input file
        except:
            self.log.error(f"No SHIP database [{filename}]")
            return
            
        line = 0  
        while(True):
            line = line + 1
            txt = Rfile.readline()          # Read the next line
            if txt == "":                   # Till empty = end
                Rfile.close()               # Close the file
                break                       # And exit the while loop

            try:
                Vmmsi = txt[0:9]
                s = int(Vmmsi)              # Check for integer number

                Vinfo = txt[10:-1]          # -1 to delete the LF or CR    

                self.SHIPmmsi.append(Vmmsi)
                self.SHIPinfo.append(Vinfo)
                # print("["+Vmmsi+"]["+Vinfo+"]")
            except:
                self.log.error(f"SHIPdata base error line: {line}")

        Rfile.close()                       # Close the file

        self.log.info(f"{filename} database inputs: {len(self.SHIPmmsi)}")