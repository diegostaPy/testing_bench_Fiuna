
FLOW_THRESHOLD = 1# LPM
class VentilatorParams():
    def __init__(self):
        self.count=0 
        self.pressure = 0.0
        self.flow = 0.0
        self.flow_last = 0.0
        self.oxygen = 0.0
        self.volume = 0.0
        self.time = 0.0
        self.time_last = 0.0
        self.fio2_accu=None
        self.fio2_mean=None
        self.pip = None
        self.peep = None
        self.ti = None
        self.te =None
        self.ie = None
        self.bpm = None
        self.pif_i = None
        self.pef_i = None
        self.pif = None
        self.pef = None
        self.vti = None
        self.vte= None
        self.tstartI=None
        self.tstartE=None
        self.MaxPI=None
        self.MinPE=None
        self.tend=None
        self.state=None # 1 inspiration 2 expiration 
        self.NewStatsReady=0 # 0 no read 1 ready
    def calculateVolume(self):
        deltaT=self.time-self.time_last
        self.volume = self.volume + self.flow*deltaT/(60.0)*1000
        self.flow_last = self.flow
        self.time_last=self.time
        if(self.tstartI):
            if((self.time-self.tstartI)>10):
                self.state=None    
    def calculateFio2(self):
        if (self.state==1 or self.state==2):
            self.fio2_accu=self.fio2_accu+self.oxygen
    def calculatePIF(self):
        if (self.state==1 and self.flow>self.pif_i):
            self.pif_i=self.flow
    def calculatePEF(self):
        if (self.state==2 and abs(self.flow)>abs(self.pef_i)):
            self.pef_i=abs(self.flow)
    def calculateMaxPressure(self):
        if (self.state==1 and self.pressure>self.MaxPI):
            self.MaxPI=self.pressure
    def calculateMinPressure(self):
        if (self.state==2 and self.pressure<self.MinPE):
            self.MinPE=self.pressure
            
    def calculateStats(self):
        self.fio2_mean=self.fio2_accu/self.count
        self.te=self.time- self.tstartE
        self.vte=self.volume-self.vti
        self.tend=self.time
        self.ie=self.te/self.ti
        self.bpm=(60.0/(self.ti+self.te))
        self.pip=self.MaxPI
        self.peep=self.MinPE
        self.pif=self.pif_i
        self.pef=self.pef_i
        self.NewStatsReady=1

    def statsReaded(self):
        self.NewStatsReady=0
        
    def defineState(self):
        
        if self.flow >FLOW_THRESHOLD and self.flow_last<FLOW_THRESHOLD and abs(self.volume)>0.2 :
            if (self.state==2):
                self.calculateStats()
            self.state=1
            self.tstartI=self.time
            self.MaxPI=self.pressure
            self.volume=0
            self.count=0
            self.fio2_accu=0
            self.pif_i=self.flow
            
        elif self.flow <-FLOW_THRESHOLD  and self.flow_last>-FLOW_THRESHOLD and self.state==1:   
            self.state=2
            self.MinPE=self.pressure
            self.ti=self.time-self.tstartI
            self.tstartE=self.time
            self.vti=self.volume
            self.pef_i=self.flow
        self.count=self.count+1
       