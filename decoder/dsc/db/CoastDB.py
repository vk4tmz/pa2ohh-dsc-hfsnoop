
import logging
import time

from decoder.dsc.config import DscConfig
from util.utils import getTimeStamp

class CoastDB:

    log: logging.Logger

    dscCfg:DscConfig

    COASTmmsi = []
    COASTname = []
    COASTlatd = []
    COASTlond = []
    COASTlat = []
    COASTlon = []

    def __init__(self, dscCfg:DscConfig):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.dscCfg = dscCfg

        if self.dscCfg.dbCoast == 1:
            self.fillMultiPSKcoast()  # Load the MultiPSKcoast data base
        elif self.dscCfg.dbCoast == 2:
            self.fillYADDcoast()          # Load the YADDcoast data base
        else:
            raise Exception(f"Invalid CoastDB Type: [{self.dscCfg.dbCoast}]")

    def lookup(self, MMSI, Country, AlwaysSave) -> int:
        # Always save if AlwaysSave == True, if False only if there is a match
        
        n = 0
        COASTindex = -1     # No valid value
        m = int(MMSI)
        while n < len(self.COASTmmsi):
            mm = int(self.COASTmmsi[n])
            if m == mm:
                COASTindex = n
                break
            n = n + 1

        if AlwaysSave == False and COASTindex == -1: # No save if no match 
            return COASTindex

        self.updateCoastStats(COASTindex, MMSI, Country)

        return COASTindex


    def updateCoastStats(self, COASTindex:int, MMSI:str, Country:str):
        # Simple Search for an UNordered short database    
        MM = []
        n = 0
        while n < 12:
            MM.append(0)
            n = n + 1

        try:
            filename = f"{self.dscCfg.dirCoast}/{MMSI}.txt"
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

        if COASTindex == -1:
            Wfile.write(Country + "\n")
            Wfile.write("Unknown name" + "\n")
            Wfile.write("0.0" + "\n")
            Wfile.write("0.0" + "\n")
        else:
            Wfile.write(Country + "\n")
            Wfile.write(self.COASTname[COASTindex] + "\n")
            Wfile.write(self.COASTlatd[COASTindex] + "\n")
            Wfile.write(self.COASTlond[COASTindex] + "\n")
        Wfile.close()


    # ... Fill the YADD coast data base ...
    def fillYADDcoast(self):

        filename = self.dscCfg.yaddCoastDB_fn

        try:
            Rfile = open(filename,'r', encoding='utf-8', errors='ignore') # Input file
            # Rfile = open(filename,'r') # Input file
        except:
            self.log.error(f"No COAST database [{filename}")
            return
                    
        line = 0
        nopos = 0 
        while(True):
            line = line + 1
            txt = Rfile.readline()          # Read the next line
            if txt == "":                   # Till empty = end
                Rfile.close()               # Close the file
                break                       # And exit the while loop

            try:
                L = txt.split(",")          # Split comma separated
                
                Vmmsi = L[0]
                s = int(Vmmsi)              # Check for integer number
            
                Vlatd = round(float(L[3]),3)
                Vlond = round(float(L[4]),3)

                if Vlatd == 0.0 and Vlond == 0.0:
                    nopos = nopos + 1

                # Calculate Vlat
                if Vlatd < 0:
                    C = "S"             # North
                    V = -1 * Vlatd
                else:
                    C = "N"             # South
                    V = Vlatd
                    
                s1 = str(int(V + 100))
                s1 = s1[1:]                         # Remove the "1"
                s2 = str(int(60 * (V % 1) + 0.5) + 100)
                s2 = s2[1:]                         # Remove the "1"            
                Vlat = s1 + "." + s2 + C

                # Calculate Vlon
                if Vlond < 0:
                    C = "W"             # West
                    V = -1 * Vlond
                else:
                    C = "E"             # East
                    V = Vlond

                s1 = str(int(V + 1000))
                s1 = s1[1:]                         # Remove the "1"
                s2 = str(int(60 * (V % 1) + 0.5) + 100)
                s2 = s2[1:]                         # Remove the "1"            
                Vlon = s1 + "." + s2 + C

                Vinfo = L[2]
            
                self.COASTmmsi.append(Vmmsi)
                self.COASTlat.append(Vlat)
                self.COASTlatd.append(str(Vlatd))            
                self.COASTlon.append(Vlon)
                self.COASTlond.append(str(Vlond))
                self.COASTname.append(Vinfo)
                # print("["+Vmmsi+"]["+Vlat+"]["+str(Vlatd)+"]["+Vlon+"]["+str(Vlond)+"]["+Vinfo+"]")
            except:
                self.log.error(f"COAST database error line: {line}")

        Rfile.close()                       # Close the file

        self.log.info(f"{filename} database inputs: {len(self.COASTmmsi)} - Without position: {nopos}")



    # ... Fill the MMSI MuliPSK coast data base ...
    def fillMultiPSKcoast(self):

        filename = self.dscCfg.multiPSKCoastDB_fn

        try:
            # Rfile = open(ilename,'r', encoding='utf-8', errors='ignore') # Input file
            Rfile = open(filename,'r') # Input file
        except:
            self.log.error(f"No COAST database [{filename}]")
            return

        nopos = 0 
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
            
                Vlat = txt[10:12] + "." + txt[13:15] + txt[16]

                Vlatd = int(txt[10:12]) + round(int(txt[13:15])/60,3)
                if txt[16] == "S":
                    Vlatd = -1 * Vlatd

                Vlon = txt[18:21] + "." + txt[22:24] + txt[25]

                Vlond = int(txt[18:21]) + round(int(txt[22:24])/60,3)
                if txt[25] == "W":
                    Vlond = -1 * Vlond

                if Vlatd == 0.0 and Vlond == 0.0:
                    nopos = nopos + 1

                Vinfo = txt[27:-1]          # -1 to delete the LF or CR
            
                self.COASTmmsi.append(Vmmsi)
                self.COASTlat.append(Vlat)
                self.COASTlatd.append(str(Vlatd))            
                self.COASTlon.append(Vlon)
                self.COASTlond.append(str(Vlond))
                self.COASTname.append(Vinfo)
                # print("["+Vmmsi+"]["+Vlat+"]["+str(Vlatd)+"]["+Vlon+"]["+str(Vlond)+"]["+Vinfo+"]")
            except:
                self.log.error(f"COAST database error line: {line}")

        Rfile.close()                       # Close the file

        self.log.info(f"{filename} database inputs: {len(self.COASTmmsi)} - Without position: {nopos}")
