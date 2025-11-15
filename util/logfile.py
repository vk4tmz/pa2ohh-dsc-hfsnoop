
from util.utils import makedirs

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