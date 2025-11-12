
import logging

from DSCConfig import DscConfig
from db.DSCDatabases import DscDatabases
from utils import getMsgVal, getMsgPaddedVals

from abc import ABCMeta, abstractmethod
from typing import Iterable, BinaryIO

DEBUG = 0

DSC_CATEGORIES = {100: "Routine", 
                  103: "Not used anymore", 
                  106: "Not used anymore",  
                  108: "Safety",
                  110: "Urgency",
                  112: "Distress"}

DSC_NATURE_OF_DISTRESS = {
    100: "Fire, Explosion",
    101: "Flooding",
    102: "Collision",
    103: "Grounding",
    104: "Listing, in danger of capsizing",
    105: "Sinking",
    106: "Disabled and adrift",
    107: "Undesignated distress",
    108: "Abandoning ship",
    109: "Piracy/armed robbery attack",
    110: "Man overboard",
    112: "Epirb emission"}

DSC_TELECOMMANDS_1 = {
    100: "F3E/G3E All modes TP",
    101: "F3E/G3E Duplex TP",
    103: "Polling",
    104: "Unable to comply",
    105: "End of call (semi-automatic service only)",
    106: "Data",
    109: "J3E TP",
    110: "Distress acknowledgement",
    112: "Distress relay",
    113: "F1B/J2B TTY-FEC",
    115: "F1B/J2B TTY-ARQ",
    118: "Test",
    121: "Ship position or location registration updating",
    126: "No Communication Mode information"}

DSC_TELECOMMANDS_2 = {
    100: "No reason",
    101: "Congestion at maritime switching centre",
    102: "Busy",
    103: "Queue indication",
    104: "Station barred",
    105: "No operator available",
    106: "Operator temporarily unavailable",
    107: "Equipment disabled",
    108: "Unable to use proposed channel",
    109: "Unable to use proposed mode",
    110: "Ship according to Resolution 18",
    111: "Medical transports",
    112: "Phone call office",
    113: "Faximile/data ITU-R M.1081",
    126: "No Availability information"}

DSC_END_OF_SEQUENCE = {
    117: "Acknowledgement required",
    122: "Acknowledgement given",
    127: "Non acknowledgements"}

#######################################################################
#  class DSCMessage
#######################################################################

class DscMessage(metaclass=ABCMeta):

    log: logging.Logger

    dscCfg: DscConfig
    dscDB: DscDatabases

    fmtSpecId: int
    fmtSpecDesc: str
    msgData: list
    expMsgData: list

    def __init__(self, fmtSpecId: int, fmtSpecDesc: str, msgData:list, expMsgData:list, dscDB:DscDatabases) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.fmtSpecId = fmtSpecId
        self.fmtSpecDesc = fmtSpecDesc
        self.msgData = msgData
        self.expMsgData = expMsgData
        self.dscDB = dscDB;
        self.dscCfg = dscDB.dscCfg

    def print(self, out: list):
        out.append(f"FMS-{self.fmtSpecId}: {self.fmtSpecDesc}")
    

#######################################################################
#  DSCMessage common utililties and Helper functions
#######################################################################

class DscZone:

    log: logging.Logger

    msgData: list
    azimuthSector:str
    latRef: str
    lonRef: str
    latBRRef: str
    lonBRRef: str

    def __init__(self, msgData:list, idx:int) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.msgData = msgData[idx:idx+5]
        
        pos = getMsgPaddedVals(msgData, idx, 5)
        
        self.azimuthSector = ""

        v = int(pos[0:1]);
        match v:
            case "0":
                self.azimuthSector = "NE"
            case "1":
                self.azimuthSector = "NW"
            case "2":
                self.azimuthSector = "SE"
            case "3":
                self.azimuthSector = "SW"
            case _:
                self.azimuthSector = ""
        
        # Top Left Corner
        self.latRef = pos[1:3]
        self.lonRef = pos[3:6]

        # Bottom Right
        self.latBRRef = pos[6:8]
        self.lonBRRef = pos[8:10]

    def print(self, out: list):
        
        txt = "Quadrant: "
        if len(self.azimuthSector) == 0:
            txt += "ERROR! NO VALID QUADRANT"
        else:
            txt += self.azimuthSector
        out.append(txt)
        
        out.append(" Latitude ref. point : " + self.latRef)
        out.append(" Longitude ref. point: " + self.lonRef)
        out.append(" Latitude N/S offset : " + self.latBRRef)
        out.append(" Longitude W/E offset: " + self.lonBRRef)


class DscCategory:
    
    log: logging.Logger
    catId: int

    def __init__(self, catId:int) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.catId = catId

    def print(self, out: list):
        Y = "NON EXISTING CATEGORY VALUE!"
        if (self.catId in DSC_CATEGORIES.keys()):
            Y = DSC_CATEGORIES[self.catId]

        out.append(f"CAT-{self.catId}: {Y}")

class DscNatureOfDistress:
    
    log: logging.Logger
    nodId: int

    def __init__(self, nodId:int) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.nodId = nodId

    def print(self, out: list):
        Y = "NON EXISTING NATURE OF DISTRESS!"
        if (self.nodId in DSC_CATEGORIES.keys()):
            Y = DSC_CATEGORIES[self.nodId]

        out.append(f"NOD-{self.nodId}: {Y}")

class DscTeleCommand1:
    
    log: logging.Logger
    tcId: int

    def __init__(self, tcId:int) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.tcId = tcId

    def print(self, out: list):
        Y = "ERROR!! NON EXISTING TELECOMMAND 1 VALUE"
        if (self.tcId in DSC_TELECOMMANDS_1.keys()):
            Y = DSC_TELECOMMANDS_1[self.tcId]

        out.append(f"TC1-{self.tcId}: {Y}")


class DscTeleCommand2:
    
    log: logging.Logger
    tcId: int

    def __init__(self, tcId:int) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.tcId = tcId

    def print(self, out: list):
        Y = "ERROR!! NON EXISTING TELECOMMAND 2 VALUE"
        if (self.tcId in DSC_TELECOMMANDS_2.keys()):
            Y = DSC_TELECOMMANDS_2[self.tcId]

        out.append(f"TC2-{self.tcId}: {Y}")


class DscMmsi:

    log: logging.Logger
    dscCfg: DscConfig
    dscDB: DscDatabases

    msgData: list
    callsign:str
    isSelfId : bool

    def __init__(self, msgData:list, idx:int, isSelfId: bool, dscDB: DscDatabases) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.msgData = msgData[idx:idx+5]
        self.callsign = getMsgPaddedVals(msgData, idx, 5)
        self.isSelfId = isSelfId
        self.dscDB = dscDB
        self.dscCfg = dscDB.dscCfg

    def mids(self, id:int) -> str:
        return self.dscDB.midsDB.lookup(id)

    def print(self, pretext:str, out: list) -> None:
# ... Decode an MMSI address ...        
        COASTindex = -1
        SHIPindex = -1
            
        callsign = self.callsign
        callsign9 = self.callsign[0:9]
        coastDB = self.dscDB.coastDB
        shipDB = self.dscDB.shipDB

        if callsign[-1:] != "0":
            out.append(f"{pretext} ERROR! MMSI [{callsign}] SHOULD END WITH A ZERO")
            return

        if callsign[0:1] != "0":                            # INDIVIDUAL
            x = int(callsign[0:3])
            out.append(f"{pretext} {callsign9} INDIVIDUAL CC{callsign[0:3]} [" + self.mids(x) + "]")

            if self.isSelfId:                          # Self ID station that transmits if True
                COASTindex = coastDB.lookup(callsign9, self.mids(x), False)    # Might be a Coast station with a "normal" MMSI in the COAST Data base
                if COASTindex == -1:                    # No match in the COAST data base
                    SHIPindex = shipDB.lookup(callsign9, self.mids(x), True)  # Is a "normal" ship MMSI, perhaps in the SHIP data base, Always save

                    # TODO: Do we need to handle this or can it go ??
                    POSmmsi = callsign9             # Callsign for possible position saving
        
        if callsign[0:1] == "0" and callsign[1:2] != "0":   # GROUP
            x = int(callsign[1:4])
            out.append(f"{pretext} {callsign9} GROUP CC{callsign[1:4]} [{self.mids(x)}]")
        
        if callsign[0:1] == "0" and callsign[1:2] == "0":   # COAST
            x = int(callsign[2:5])
            out.append(f"{pretext} {callsign9} COAST CC{callsign[2:5]} [{self.mids(x)}]")
            if self.isSelfId == True:                          # Self ID station that transmits if True
                COASTindex = coastDB.lookup(callsign, self.mids(x), True)     # Check the COAST data base and True=ALWAYS save
                if COASTindex == -1:                    # NOT a match!
                    out.append(f"{pretext} Unknown Coast station: {callsign9}")

        if COASTindex != -1:                            # A match in the COAST data base
            out.append(f"INFO-DB: [{coastDB.COASTname[COASTindex]}  {coastDB.COASTlat[COASTindex]} {coastDB.COASTlon[COASTindex]}]")
        if SHIPindex != -1:
            out.append(f"INFO-DB: [{shipDB.SHIPinfo[SHIPindex]}]")
        

class DscPosition:

    LATchar: str = ""
    LONchar: str = ""
    lat: float = 0.0
    lon: float = 0.0

    position: str = ""
    validQuadrant: bool = True
    posRequested: bool = False
    intPosErrFlag: int = 0

    def __init__(self, msgData:list, idx:int) -> None:
        self.intPosErrFlag = 0
    
        # Scan Position values for invalid values
        for N in range (idx, idx+5):
            v = getMsgVal(msgData, N)
            if v != 126 and v > 99:
                self.intPosErrFlag = 1

        if (self.intPosErrFlag != 0):
            return
        
        if (getMsgVal(msgData, idx) == 126):
            self.posRequested = True
        else:
            # ... Position ...
            self.position = getMsgPaddedVals(msgData, idx, 5)
            
            self.LATchar = ""
            self.LONchar = ""
            match int(self.position[0:1]):
                case 0:
                    self.LATchar = "N"
                    self.LONchar = "E"
                case 1:
                    self.LATchar = "N"
                    self.LONchar = "W"
                case 2:
                    self.LATchar = "S"
                    self.LONchar = "E"
                case 3:
                    self.LATchar = "S"
                    self.LONchar = "W"
                case _:
                    self.validQuadrant = False

            lat = int(self.position[1:3]) + float(self.position[3:5]) / 60
            lat = round(lat,3)
            if self.LATchar == "S":
                lat = -1 * lat

            self.lat = lat;

            lon = int(self.position[5:8]) + float(self.position[8:10]) / 60
            lon = round(lon,3)
            if self.LONchar == "W":
                lon = -1 * lon

            self.lon = lon;


    def print(self, out: list):

        txt = "LOCATED: "
        
        if self.intPosErrFlag == 1:
            txt = txt + "ERROR! NO VALID POSITION"
        elif self.posRequested:
            txt = txt + "POSITION REQUEST"
        elif self.position == "9999999999":
            txt =  txt + "NO POSITION"
        elif int(self.position[0:1]) > 3:
            txt = txt + "ERROR! NO VALID QUADRANT"
        else:

            latStr = self.position[1:3] + "-" + self.position[3:5] + self.LATchar
            lonStr = self.position[5:8] + "-" + self.position[8:10] + self.LONchar
                
            txt = txt + latStr + " " + lonStr

            # Open Street Map link
            # https://www.openstreetmap.org/?mlat=53.2323&mlon=6.0631#map=10/53.2323/6.0631
            OSlink = "HTTPS://www.openstreetmap.org/?mlat="+str(self.lat)+"&mlon="+str(self.lon)+"#map=10/"+str(self.lat)+ "/"+str(self.lon);

            out.append(txt);
            out.append("WEBLINK: " + OSlink);

class DscUtcTime:

    strUTC: str

    def __init__(self, msgData:list, idx:int) -> None:
        # ... Decode a time in UTC ...    
        self.strUTC = getMsgPaddedVals(msgData, idx, 10)
        
    
    def print(self, out: list):
        txt = ""
    
        if self.strUTC == "8888":
            txt = txt + "UTCTIME: None"
        else:
            txt = txt + "UTCTIME: " + self.strUTC

        out.append(txt)


class DscFrequency:

    hasFrequency: bool = True    
    isExtFreq:bool = False              # Normaly 4 bytes, but True if Freq has 1 extra bit/byte in msg
    isPosition: bool = False
    intFreqErrFlag: int = 0

    frequency:str
    freqLength: int = 3

    def __init__(self, msgData:list, idx:int) -> None:
        # ... Decode a frequency ...
        self.intFreqErrFlag = 0

        if getMsgVal(msgData, idx) == 55:
            self.isPosition = True
            return
        
        if int(getMsgVal(msgData, idx) / 10) == 4:   # Extended frequency 10 Hz resolution
            self.freqLength = 4                              #  if "4" in accordance with R-REC-M.493-15-201901
            self.isExtFreq = True                    # One extra bit in the message string
        else:
            self.freqLength = 3 
        
        self.frequency = getMsgPaddedVals(msgData, idx, self.freqLength)

        # Scan frequency values for invalid values
        for N in range (idx, idx+self.freqLength):
            v = getMsgVal(msgData, N)
            if v != 126 and v > 99:
                self.intPosErrFlag = 1

        if (getMsgVal(msgData, idx) == 126):
            self.hasFrequency = False
        


    def print(self, pretext: str, out: list):

        if self.isPosition:
            out.append(f"{pretext} ERROR: POSITION NO FREQUENCY")
            return

        if self.intFreqErrFlag == 1:
            out.append(f"ERROR: SYMBOL VALUE OUTSIDE RANGE 0 - 99 - [{self.frequency}].")
            return

        if not self.hasFrequency:
            out.append(f"{pretext} NONE")
            return

        if self.frequency[0] == "9":          # VHF channel!   
            if self.frequency[1] != "0":
                out.append(f"{pretext} VHF CHANNEL ERROR! FIRST TWO DIGITS SHOULD BE 90!")
                return
        
            if int(self.frequency[2]) > 2:
                out.append(f"{pretext} VHF CHANNEL ERROR! THIRD CHARACTER SHOULD BE LESS THAN 3!")
                return
            
            if self.frequency[2] == "0":     
                # "Frequency in accordance with RR Appendix 18 "
                pass
            
            if self.frequency[2] == "1":
                # "This frequency is simplex for ship and coast station"
                pass
            
            if self.frequency[2] == "2":
                # "Other frequency is simplex for ship and coast station"
                pass
            
            # ... VHF Channel ...
            out.append(f"{pretext} {self.frequency[3:6]} VHF-CHANNEL")
            return

        if int(self.frequency[0]) < 3:
            # ... Frequency ...
            out.append(f"{pretext}  {str(round(float(self.frequency[0:6])/10,1))} kHz")
            return

        if self.frequency[0] == "3":
            # ... Frequency ...
            out.append(f"{pretext} {self.frequency[1:6]} HF-CHANNEL")
            return

        if self.isExtFreq:            # Extended frequency 10 Hz resolution in accordance with R-REC-M.493-15-201901
            # ... Frequency[0] = "4" ...
            out.append(f"{pretext} {str(round(float(self.frequency[1:8])/100,2))} kHz")
            return

        if self.frequency[0] == "8":
            # ... Frequency ...
            out.append(f"{pretext} {self.frequency[0:6]} AUTOMATED EQUIPMENT")
            return
        
        out.append(f"{pretext} {self.frequency[0:6]}")


class DscEndOfSequence:
    
    log: logging.Logger
    eosId: int

    def __init__(self, eosId:int) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.eosId = eosId

    def print(self, out: list):
        Y = "ERROR!! NON EXISTING EOS VALUE"
        if (self.eosId in DSC_END_OF_SEQUENCE.keys()):
            Y = DSC_END_OF_SEQUENCE[self.eosId]

        out.append(f"EOS-{self.eosId}: {Y}")


#######################################################################
#  class DscSelectiveGeographicAreaMsg - FS102
#######################################################################

class DscSelectiveGeographicAreaMsg(DscMessage):

    log: logging.Logger

    zone: DscZone
    cat: DscCategory

    selfId: DscMmsi
    tc1: DscTeleCommand1
    tc2: DscTeleCommand2
    distId: DscMmsi
    nod: DscNatureOfDistress
    pos: DscPosition
    subComm: DscTeleCommand1
    freqRx: DscFrequency
    freqTx: DscFrequency

    eos: DscEndOfSequence

    def __init__(self, msgData:list, expMsgData:list, dscDB:DscDatabases) -> None:
        super().__init__(102, "Selective geographic area", msgData, expMsgData, dscDB)
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))

        self.zone = DscZone(msgData, 1)
        self.cat = DscCategory(getMsgVal(msgData, 6))
        
        match self.cat.catId:
            case 112:
                self.selfId = DscMmsi(msgData, 7, True, self.dscDB)
                self.tc1 = DscTeleCommand1(getMsgVal(msgData, 12))
                self.distId = DscMmsi(msgData, 13, False, self.dscDB)
                self.nod = DscNatureOfDistress(getMsgVal(msgData, 18))
                self.pos = DscPosition(msgData, 19)
                self.timeUtc = DscUtcTime(msgData, 24)
                self.subComm = DscTeleCommand1(getMsgVal(msgData, 26))
            case 108 | 110:
                self.selfId = DscMmsi(msgData, 7, True, self.dscDB)
                self.tc1 = DscTeleCommand1(getMsgVal(msgData, 12))
                self.tc2 = DscTeleCommand2(getMsgVal(msgData, 13))
                self.freqRx = DscFrequency(msgData, 14)
                self.freqTx = DscFrequency(msgData, 14+self.freqRx.freqLength)

        self.eos = DscEndOfSequence(getMsgVal(msgData, len(msgData) - 2))

        # TODO: Need to handle detectng invalid message (ie excepion for scan each of the possible fields for a status flag ?)
        # MSGstatus = 3       # Continue with the next search, messages have been decoded

    def print(self, out: list):
        super().print(out)

        self.zone.print(out)
        self.cat.print(out)
        
        if self.cat.catId == 112:                           # Category 112
            self.selfId.print("SELF-ID:", out)
            self.tc1.print(out)
            self.distId.print("DIST-ID:", out)
            self.nod.print(out)
            self.pos.print(out)
            self.timeUtc.print(out)
            self.subComm.print(out);

        if self.cat.catId in [108, 110]:                    # Category 108 or 110 
            self.selfId.print("SELF-ID:", out)
            self.tc1.print(out)
            self.tc2.print(out)
            self.freqRx.print("FREQ-RX:", out)
            self.freqTx.print("FREQ-TX:", out)
        
        self.eos.print(out)
                

#######################################################################
#  class DscDistressAlertMsg - FS112
#######################################################################

class DscDistressAlertMsg(DscMessage):

    log: logging.Logger

    selfId: DscMmsi
    nod: DscNatureOfDistress
    pos: DscPosition
    subComm: DscTeleCommand1
    freqRx: DscFrequency
    freqTx: DscFrequency

    eos: DscEndOfSequence

    def __init__(self, msgData:list, expMsgData:list, dscDB:DscDatabases) -> None:
        super().__init__(112, "Distress", msgData, expMsgData, dscDB)
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))

        # TODO: Need to ensure UI is notified
        #SPECIAL()           # Special message

        self.selfId = DscMmsi(msgData, 1, False, self.dscDB)
        self.nod = DscNatureOfDistress(getMsgVal(msgData, 6))
        self.pos = DscPosition(msgData, 7)
        self.timeUtc = DscUtcTime(msgData, 12)
        self.subComm = DscTeleCommand1(getMsgVal(msgData, 14))
        self.eos = DscEndOfSequence(getMsgVal(msgData, len(msgData) - 2))

        # MSGstatus = 3       # Continue with the next search, messages have been decoded


    def print(self, out: list):
        super().print(out)
        
        # TODO: original logic use "DIST-ID" as pretext ? but spec clearly calls this field "SELF-ID"
        self.selfId.print("SELF-ID:", out)
        self.nod.print(out)
        self.pos.print(out)
        self.timeUtc.print(out)
        self.subComm.print(out);
        self.eos.print(out)



#######################################################################
#  class DscRoutineGroupCallMsg - FS114
#######################################################################

class DscRoutineGroupCallMsg(DscMessage):

    log: logging.Logger

    adrsId: DscMmsi
    cat: DscCategory
    selfId: DscMmsi
    tc1: DscTeleCommand1
    tc2: DscTeleCommand2
    freqRx: DscFrequency
    freqTx: DscFrequency

    eos: DscEndOfSequence

    def __init__(self, msgData:list, expMsgData:list, dscDB:DscDatabases) -> None:
        super().__init__(114, "Routine group call", msgData, expMsgData, dscDB)
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))

        self.adrsId = DscMmsi(msgData, 1, False, self.dscDB)
        self.cat = DscCategory(getMsgVal(msgData, 6))
        self.selfId = DscMmsi(msgData, 7, False, self.dscDB)
        self.tc1 = DscTeleCommand1(getMsgVal(msgData, 12))

        match self.cat.catId:
            case 112:                   # Distress Alert Relay Ack
                # TODO: Only for VHF so to be done in future
                self.log.warning("VHF - Distress Alert Relay Ack not currently not handled.")
                pass
            case 100:
                self.tc2 = DscTeleCommand2(getMsgVal(msgData, 13))
                self.freqRx = DscFrequency(msgData, 14)
                self.freqTx = DscFrequency(msgData, 14+self.freqRx.freqLength)
            case _:
                self.log.error(f"DscRoutineGroupCallMsg: Unhandled category code: [{self.cat.catId}]")

        self.eos = DscEndOfSequence(getMsgVal(msgData, len(msgData) - 2))

        # MSGstatus = 3       # Continue with the next search, messages have been decoded


    def print(self, out: list):
        super().print(out)

        self.adrsId.print("ADRS-ID:", out)
        self.cat.print(out)
        self.selfId.print("SELF-ID:", out)
        self.tc1.print(out)

        match self.cat.catId:
            case 112:                   # Distress Alert Relay Ack - VHF
                # TODO: Only for VHF so to be done in future
                self.log.warning("VHF - Distress Alert Relay Ack not currently not handled.")
                pass
            case 100:
                self.tc2.print(out)
                self.freqRx.print("FREQ-RX:", out)
                self.freqTx.print("FREQ-TX:", out)
            case _:
                self.log.error(f"DscRoutineGroupCallMsg: Unhandled category code: [{self.cat.catId}]")

        self.eos.print(out)
    
    

#######################################################################
#  class DscAllShipCallMsg - FS116
#######################################################################

class DscAllShipCallMsg(DscMessage):
    
    cat: DscCategory
    selfId: DscMmsi
    distId: DscMmsi
    nod: DscNatureOfDistress
    pos: DscPosition
    utcTime: DscUtcTime
    subComm: DscTeleCommand1

    tc1: DscTeleCommand1
    tc2: DscTeleCommand2
    freqRx: DscFrequency
    freqTx: DscFrequency

    eos: DscEndOfSequence

    def __init__(self, msgData:list, expMsgData:list, dscDB:DscDatabases) -> None:
        super().__init__(116, "All ships call", msgData, expMsgData, dscDB)
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
       
        self.cat = DscCategory(getMsgVal(msgData, 1))

        match self.cat.catId:
            case 112:                   # Distress Ack
                self.selfId = DscMmsi(msgData, 2, True, self.dscDB)
                self.tc1 = DscTeleCommand1(getMsgVal(msgData, 7))
                self.distId = DscMmsi(msgData, 8, False, self.dscDB)
                self.nod = DscNatureOfDistress(getMsgVal(msgData, 13))
                self.pos = DscPosition(msgData, 14)
                self.timeUtc = DscUtcTime(msgData, 19)
                self.subComm = DscTeleCommand1(getMsgVal(msgData, 21))
            case 108 | 110:              # Urgency and Safety Calls - All shi[s]
                self.selfId = DscMmsi(msgData, 2, True, self.dscDB)
                self.tc1 = DscTeleCommand1(getMsgVal(msgData, 7))
                self.tc2 = DscTeleCommand2(getMsgVal(msgData, 8))
                self.freqRx = DscFrequency(msgData, 9)
                self.freqTx = DscFrequency(msgData, 9+self.freqRx.freqLength)
            case _:
                self.log.error(f"DscAllShipCallMsg: Unhandled category code: [{self.cat.catId}]")

        self.eos = DscEndOfSequence(getMsgVal(msgData, len(msgData) - 2))


    def print(self, out: list):
        super().print(out)

        self.cat.print(out)

        match self.cat.catId:
            case 112:
                self.selfId.print("SELF-ID:", out)
                self.tc1.print(out)
                self.distId.print("DIST-ID:", out)
                self.nod.print(out)
                self.pos.print(out)
                self.timeUtc.print(out)
                self.subComm.print(out);
            case 108 | 110:
                self.selfId.print("SELF-ID:", out)
                self.tc1.print(out)
                self.tc2.print(out)
                self.freqRx.print("FREQ-RX:", out)
                self.freqTx.print("FREQ-TX:", out)
            case _:
                self.log.error(f"DscAllShipCallMsg: Unhandled category code: [{self.cat.catId}]")    

        self.eos.print(out)


#######################################################################
#  class DscSelectiveIndividualCallMsg - FS120
#######################################################################

class DscSelectiveIndividualCallMsg(DscMessage):

    isTestMsg: bool = False

    cat: DscCategory
    selfId: DscMmsi
    distId: DscMmsi
    nod: DscNatureOfDistress
    pos: DscPosition
    utcTime: DscUtcTime
    subComm: DscTeleCommand1

    tc1: DscTeleCommand1
    tc2: DscTeleCommand2
    freqRx: DscFrequency
    freqTx: DscFrequency

    eos: DscEndOfSequence

    def __init__(self, msgData:list, expMsgData:list, dscDB:DscDatabases) -> None:
        super().__init__(120, "Selective individual call", msgData, expMsgData, dscDB)
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
       
        self.adrsId = DscMmsi(msgData, 1, False, self.dscDB)
        self.cat = DscCategory(getMsgVal(msgData, 6))
        
        match self.cat.catId:
            case 100: 
                self.selfId = DscMmsi(msgData, 7, True, self.dscDB)
                self.tc1 = DscTeleCommand1(getMsgVal(msgData, 12))
                self.tc2 = DscTeleCommand2(getMsgVal(msgData, 13))
                if getMsgVal(msgData, 14) == 55:                   # Position update 1st frequency symbol=55
                    pos = DscPosition(msgData, 15)
                    
                    # TODO: Need to refactor the SAVEpos() logic
                    # SAVEpos()                           # Save the ship position

                    if getMsgVal(msgData, 20) < 100:               # No EOS but time
                        self.utcTime = DscUtcTime(msgData, 20)

                else:    
                    self.freqRx = DscFrequency(msgData, 14)
                    self.freqTx = DscFrequency(msgData, 14+self.freqRx.freqLength)

            case 112:           # Distress Alert Relays & Ack
                self.selfId = DscMmsi(msgData, 7, True, self.dscDB)
                self.tc1 = DscTeleCommand1(getMsgVal(msgData, 12))
                self.distId = DscMmsi(msgData, 13, False, self.dscDB)
                self.nod = DscNatureOfDistress(getMsgVal(msgData, 18))
                self.pos = DscPosition(msgData, 19)
                self.timeUtc = DscUtcTime(msgData, 24)
                self.subComm = DscTeleCommand1(getMsgVal(msgData, 26))
            case 108 | 110:
                if getMsgVal(msgData, 12) == 118 and getMsgVal(msgData, 14) == 126:   # Test message
                    self.isTestMsg = True                                             # It is a test message and continue with decoding

                self.selfId = DscMmsi(msgData, 7, True, self.dscDB)
                self.tc1 = DscTeleCommand1(getMsgVal(msgData, 12))
                self.tc2 = DscTeleCommand2(getMsgVal(msgData, 13))

                if getMsgVal(msgData, 14) == 55:                   # Position update 1st frequency symbol=55
                    pos = DscPosition(msgData, 15)
                    
                    # TODO: Need to refactor the SAVEpos() logic
                    # SAVEpos()                           # Save the ship position

                    if getMsgVal(msgData, 20) < 100:               # No EOS but time
                        self.utcTime = DscUtcTime(msgData, 20)

                else:    
                    self.freqRx = DscFrequency(msgData, 14)
                    self.freqTx = DscFrequency(msgData, 14+self.freqRx.freqLength)

            case _:
                pass

        self.eos = DscEndOfSequence(getMsgVal(msgData, len(msgData) - 2))


    def print(self, out: list):
        super().print(out)

        self.adrsId.print("ADRS-ID:", out)
        self.cat.print(out)

        match self.cat.catId:
            case 100:
                self.selfId.print("SELF-ID:", out)
                self.tc1.print(out)
                self.tc2.print(out)
                # if (self.pos is not None):
                if hasattr(self, "pos"):
                    self.pos.print(out)
                    # if (self.utcTime is not None):
                    if hasattr(self, "utcTime"):
                        self.utcTime.print(out)
                else:
                    self.freqRx.print("FREQ-RX:", out)
                    self.freqTx.print("FREQ-TX:", out)
            case 108 | 110:
                self.selfId.print("SELF-ID:", out)
                self.tc1.print(out)
                self.tc2.print(out)
                # if (self.pos is not None):
                if hasattr(self, "pos"):
                    self.pos.print(out)
                    # if (self.utcTime is not None):
                    if hasattr(self, "utcTime"):
                        self.utcTime.print(out)
                else:
                    self.freqRx.print("FREQ-RX:", out)
                    self.freqTx.print("FREQ-TX:", out)

            case 112:
                self.selfId.print("SELF-ID:", out)
                self.tc1.print(out)
                self.distId.print("DIST-ID:", out)
                self.nod.print(out)
                self.pos.print(out)
                self.timeUtc.print(out)
                self.subComm.print(out);

        self.eos.print(out)
