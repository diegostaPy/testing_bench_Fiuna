
FLOW_THRESHOLD_H = 0.5# LPM

FLOW_THRESHOLD_L = 1# LPM
class VentilatorParams():
    def __init__(self):
        self.count=0
        self.countE=0
        self.pressure = 0.0
        self.flow = 0.0
        self.flow_last = 0.0
        self.oxygen = 0.0
        self.volume = 0.0
        self.time = 0.0
        self.time_last = 0.0
        self.fio2_accu=0.0
        self.fio2_mean=None
        self.pip = None
        self.peep = None
        self.ti = None
        self.te =None
        self.ie = None
        self.bpm = None
        self.pif_i = 0.0
        self.pef_i = 0.0
        self.pif = None
        self.pef = None
        self.vti = None
        self.vte= None
        self.tstartI=0.0
        self.tstartE=None
        
        self.MaxPI=0.0
        self.MinPE=0.0
        self.tend=None
        self.state=0 # 1 inspiration 2 expiration 
        self.NewStatsReady=0 # 0 no read 1 ready
    def calculateVolume(self):
        deltaT=self.time-self.time_last
        self.volume = self.volume + self.flow*deltaT/(60.0)*1000
        self.flow_last= self.flow
        self.time_last=self.time
        if(self.tstartI):
            if((self.time-self.tstartI)>12):
                self.state=0   
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
        self.te=self.time-self.tstartE
        self.vte=abs(self.volume-self.vti)
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
        #print(str(self.state)+" "+str(self.flow)+" "+str(self.flow_last)+" "+str(self.count-self.countE))
        if self.flow >FLOW_THRESHOLD_H and self.flow_last<FLOW_THRESHOLD_H and(self.count-self.countE>5)and (self.state==0 or self.state==2) :
            if (self.state==2):
            #    print(self.ti,self.te,self.tstartI,self.tstartE,self.time)
                self.calculateStats()
            self.state=1
            self.tstartI=self.time
            self.MaxPI=self.pressure
            self.volume=0
            self.count=0
            self.countE=0
            self.fio2_accu=0
            self.pif_i=self.flow
            
        elif self.flow <-FLOW_THRESHOLD_L  and self.flow_last>-FLOW_THRESHOLD_L and(self.count-self.countE>5)and self.state==1:   
            self.state=2
            self.MinPE=self.pressure
            self.ti=self.time-self.tstartI
            self.tstartE=self.time
            self.vti=self.volume
            self.pef_i=self.flow
            self.countE=self.count
            
        self.count=self.count+1
       