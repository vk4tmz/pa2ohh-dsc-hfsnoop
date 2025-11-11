
import logging

from DSCConfig import DscConfig
from CoastDB import CoastDB
from ShipDB import ShipDB

class DscDatabases:

    log: logging.Logger
    dscCfg:DscConfig

    coastDB: CoastDB
    shipDB: ShipDB

    def __init__(self, dscCfg:DscConfig):
        self.log = logging.getLogger("%s.%s" % (__name__, self.__class__.__name__))
        self.dscCfg = dscCfg

        self.coastDB = CoastDB(dscCfg)
        self.shipDB = ShipDB(dscCfg)
