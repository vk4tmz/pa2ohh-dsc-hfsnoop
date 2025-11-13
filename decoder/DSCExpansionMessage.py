
import logging

from db.DSCDatabases import DscDatabases
from utils import getMsgVal, getMsgPaddedVals, getMsgPaddedValsVarLen, getMsgValsVarLen, popLeft

from collections import deque

# ITU-R M.821-1 Table 2.
EXP_MSG_ALPHANUMERIC = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "?",
                        "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", 
                        "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", 
                        "W", "X", "Y", "Z", ".", ",", "-", "/", " "]

EXP_MSG_POSITION_SOURCE = {
    0: "Current position data invalid",
    1: "Position data from differential GPS",
    2: "Position data from uncorrected GPS",
    3: "Position data from differential LORAN-C",
    4: "Position data from uncorrected LORAN-C",
    5: "Position data from GLONASS",
    6: "Position data from radar fix",
    7: "Position data from Decca",
    8: "Position data from other source",
}

EXP_MSG_POSITION_DATUM = {
        0: "WGS-84",
        1: "WGS-72",
        2: "Other"
}

EXP_MSG_CMD = {
    0:   "Valid Data",
    110: "Enhanced position data request",
    126: "No enhanced position information"
}


#######################################################################
#  class DscExpansionMessage
#######################################################################

class DscExpansionMessage():

    cmd:int=0         # 0 - Has Data,  110 - Data Request, 126 - No Data Available

    expSpecId: int
    expSpecDesc: str
    expMsgData: deque
    dscDB: DscDatabases

    def __init__(self, expSpecId: int, expSpecDesc: str, expMsgQ:deque) -> None:
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))

        self.expSpecId = expSpecId
        self.expSpecDesc = expSpecDesc
        self.expMsgData = expMsgQ

        # Check for and process Command Val
        v = expMsgQ[0]
        if (v in [110,126]):
            self.cmd = v
            popLeft(expMsgQ, 1)


    def print(self, out: list):
        out.append(f"EMS-{self.expSpecId:03d}: {self.expSpecDesc}")


#######################################################################
#  class DscEhancedPositionResolutionMsg
#######################################################################

class DscEhancedPositionResolutionMsg(DscExpansionMessage):

    lat_ext: float
    lon_ext: float

    def __init__(self, emq:deque) -> None:
        super().__init__(100, "Enhanced position resolution", emq)

        if (self.cmd == 0):
            strX = getMsgPaddedVals(emq, 0, 10)
            self.lat = float("0." + strX[0:4])
            self.lon = float("0." + strX[4:9])
            popLeft(emq, 10)

    def print(self, out: list):
        super().print(out)

        if self.cmd > 0:
            out.append(f"EHN-POS: {EXP_MSG_CMD[self.cmd]}")
        else:
            
            out.append(f"EHN-POS: Latitude : {self.lat:0.05f}")
            out.append(f"EHN-POS: Longitude: {self.lon:0.05f}")


#######################################################################
#  class DscPositionSourceAndDatumMsg
#######################################################################

class DscPositionSourceAndDatumMsg(DscExpansionMessage):

    navRxType: int
    fixedRes: float
    datum:  int
    

    def __init__(self, emq:deque) -> None:
        super().__init__(101, "Source and datum of position", emq)

        if (self.cmd == 0):         
            self.navRxType = getMsgVal(emq, 0)       # Table 4

            v = getMsgVal(emq, 1)  #
            if (v >= 99):                   # any value >= 9.9 should be indicated by 99
                self.fixedRes = 99.0
            else:
                self.fixedRes = v / 10

            self.datum = getMsgVal(emq, 2)

            popLeft(emq, 3)

    def print(self, out: list):
        super().print(out)

        if self.cmd > 0:
            out.append(f"EHN-SRC: {EXP_MSG_CMD[self.cmd]}")
        else:
            if (self.navRxType in EXP_MSG_POSITION_SOURCE):
                src = EXP_MSG_POSITION_SOURCE[self.navRxType]
            else:
                src = f"[{self.navRxType}] ERROR!! INVALID SOURCE CHARACTER"
            out.append(f"EHN-SRC: {src}")
            out.append(f"EHN-FIX: {self.fixedRes:0.01f}")

            if (self.datum in EXP_MSG_POSITION_DATUM):
                dat = EXP_MSG_POSITION_DATUM[self.datum]
            else:
                dat = f"[{self.navRxType}] ERROR!!  INVALID DATUM CHARACTER"
                            
            out.append(f"EHN-DAT: {dat}")


#######################################################################
#  class DscVesselCurrentSpeedMsg
#######################################################################

class DscVesselCurrentSpeedMsg(DscExpansionMessage):

    speed: float

    def __init__(self, emq:deque) -> None:
        super().__init__(102, "Vessel speed", emq)

        if (self.cmd == 0):
            strX = getMsgPaddedVals(emq, 0, 4)
            self.speed = float(strX[0:3])
            self.speed += int(strX[3])/10
            popLeft(emq, 4)

    def print(self, out: list):
        super().print(out)

        if self.cmd > 0:
            out.append(f"EHN-VCS: {EXP_MSG_CMD[self.cmd]}")
        else:
            out.append(f"EHN-VCS: Speed: {self.speed:0.02f} knots")
                

#######################################################################
#  class DscVesselCurrentCourse
#######################################################################

class DscVesselCurrentCourseMsg(DscExpansionMessage):

    course: float

    def __init__(self, emq:deque) -> None:
        super().__init__(103, "Vessel course", emq)

        if (self.cmd == 0):
            strX = getMsgPaddedVals(emq, 0, 4)
            self.course = float(strX[0:3])
            self.course += int(strX[3])/10
            popLeft(emq, 4)

    def print(self, out: list):
        super().print(out)

        if self.cmd > 0:
            out.append(f"EHN-VCC: {EXP_MSG_CMD[self.cmd]}")
        else:
            out.append(f"EHN-VCC: Course: {self.course:0.02f} Degrees")


#######################################################################
#  class DscAdditionalInformation
#######################################################################

class DscAdditionalInformationMsg(DscExpansionMessage):

    info: str

    def __init__(self, emq:deque) -> None:
        super().__init__(104, "Additional station information", emq)

        if (self.cmd == 0):
            self.info = ""

            vals = getMsgValsVarLen(emq, 0)
            for v in vals:
                if v <= 41:
                    self.info += EXP_MSG_ALPHANUMERIC[v]
                else: 
                    self.info += "?"
                            
            popLeft(emq, len(vals))

    def print(self, out: list):
        super().print(out)

        if self.cmd > 0:
            out.append(f"EHN-INF: {EXP_MSG_CMD[self.cmd]}")
        else:
            out.append(f"EHN-INF: [{self.info}]")


#######################################################################
#  class DscAdditionalInformation
#######################################################################

class DscEnhancedGeographicAreaMsg(DscExpansionMessage):

    latRefPoint: float
    lonRefPoint: float
    latOffset: float
    lonOffset: float

    speed: DscVesselCurrentSpeedMsg
    course: DscVesselCurrentCourseMsg

    def __init__(self, emq:deque) -> None:
        super().__init__(105, "Enhanced geographic area position information", emq)

        if (self.cmd == 0):
            strX = getMsgPaddedVals(emq, 0, 8)
            self.latRefPoint = float("0." + strX[0:4]);
            self.lonRefPoint = float("0." + strX[4:8]);
            self.latOffset = float("0." + strX[8:12]);
            self.lonOffset = float("0." + strX[12:16]);
            popLeft(emq, 8)
            
            self.speed = DscVesselCurrentSpeedMsg(emq)
            popLeft(emq, 2) # If cmd=126 the 2nd 126 will be popped

            self.course = DscVesselCurrentCourseMsg(emq)
            popLeft(emq, 2) # If cmd=126 the 2nd 126 will be popped

            

    def print(self, out: list):
        super().print(out)

        if self.cmd > 0:
            out.append(f"EHN-GEO: {EXP_MSG_CMD[self.cmd]}")
        else:
            out.append(f"EHN-GEO: Latitude ref. point : [{self.latRefPoint}]")
            out.append(f"EHN-GEO: Longitude ref. point: [{self.lonRefPoint}]")
            out.append(f"EHN-GEO: Latitude offset     : [{self.latOffset}]")
            out.append(f"EHN-GEO: Longitude offset    : [{self.lonOffset}]")
            out.append(" ")
            self.speed.print(out)
            self.course.print(out)



#######################################################################
#  class DscVesselCurrentCourseMsg
#######################################################################

class DscNumberPersonsOnBoardMsg(DscExpansionMessage):

    pob: int

    def __init__(self, emq:deque) -> None:
        super().__init__(106, "Number of persons on board", emq)

        if (self.cmd == 0):
            strX = getMsgPaddedVals(emq, 0, 2)
            self.pob = int(strX)
            popLeft(emq, 4)

    def print(self, out: list):
        super().print(out)

        if self.cmd > 0:
            out.append(f"EHN-POB: {EXP_MSG_CMD[self.cmd]}")
        else:
            out.append(f"EHN-POB: Number of persons: {self.pob}")


