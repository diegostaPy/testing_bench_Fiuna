#!/usr/bin/python3
import datetime
from datetime import timedelta, timezone

import os
import numpy as np
from subprocess import Popen,PIPE
import time
from ventparamsNew import VentilatorParams
from kivy.properties import ObjectProperty, StringProperty
from kivy.config import Config
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy_garden.graph import Graph, LinePlot
from kivy.uix.screenmanager import ScreenManager, Screen

from pipyadc.ADS1256_definitions import *
from pipyadc import ADS1256
import pipyadc.ADS1256_default_config as myconfig_2

fio2= POS_AIN0|NEG_AINCOM
pressure= POS_AIN1|NEG_AINCOM
flow= POS_AIN2|NEG_AINCOM
CH_SEQUENCE = (fio2,pressure,flow)
CH_OFFSET = np.array((0,   0, 0), dtype=np.int64)
GAIN_CAL  = np.array((1.0, 1.0,1.0), dtype=np.float64)
VERDE=(0.0, 0.7, 0.0, 1.0)
NEGRO=(0.15, 0.15, 0.15, 1.0)
Config.set('kivy', 'keyboard_mode', 'systemanddock')
#Config.set('graphics', 'fullscreen', '1')
#Config.set('graphics', 'show_cursor', '0')
#Config.set('graphics', 'height', '720')
#Config.set('graphics', 'width', '1080')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'show_cursor', '1')
Config.set('graphics', 'height', '440')
Config.set('graphics', 'width', '600')

Config.write()


record_time = ''
CSV_file_name = 'default'
count = 0
ix=0


refreshRate=1.0/30.0
FILTER_SIZE = 5

dirPath='logs'
if not os.path.isdir(dirPath):
    os.mkdir(dirPath)
os.system('rm '+dirPath+'/*')
logfilename=dirPath+'/log.csv'




class WindowManager(ScreenManager):
    pass

class AdvertenciaPopUp(Popup):
    pass

class RecordWindow(Screen):
    file_name = ObjectProperty(None)
    min = ObjectProperty(None)
    sec = ObjectProperty(None)
   
    def accept(self):
        global Recording,RecordingCanceled, CSV_file_name, record_time,Sampleproc 
        try:
            print(self.min.text, self.sec.text,self.file_name.text)
            record_time = datetime.datetime.now() + timedelta(minutes=int(self.min.text), seconds=int(self.sec.text))
            if self.file_name.text != '':
                CSV_file_name = self.file_name.text+'.csv'
            self.file_name.text = ''
            self.min.text = ''
            self.sec.text = ''
            Recording= True
            Sampleproc = Popen("python3 sampler.py " + CSV_file_name,stdout=PIPE, stderr=PIPE, shell=True,preexec_fn=os.setsid)
            App.get_running_app().root.current = "main"
            self.manager.transition.direction = "up"
        except:
            AdvertenciaPopUp().open()
             


    def cancel(self):
        global RecordingCanceled
        RecordingCanceled = True

class ClockText(Label):
    def __init__(self, *args, **kwargs):
        super(ClockText, self).__init__(*args, **kwargs)
        Clock.schedule_interval(self.update, 1)

    def update(self, *args):
        self.text = time.strftime('%I:%M:%S %p')
    

class ConfigTab(TabbedPanel):
    pass
   

class MainWindow(Screen):
    
    graph_P = ObjectProperty(Graph())
    graph_F = ObjectProperty(Graph())
    graph_V = ObjectProperty(Graph())
    
    pip_string = StringProperty("--")
    peep_string = StringProperty("--")
    ti_string = StringProperty("--")
    fio2_string= StringProperty("--")
    ie_string = StringProperty("--")
    bpm_string = StringProperty("--")
    pif_string = StringProperty("--")
    vti_string = StringProperty("--")


    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
       #global EnableShow,EnableGraph,EnableRecord
        self.EnableShow=False
        self.EnableGraph=False
        self.EnableRecord=False
        global Recording,RecordingCanceled
        Recording=False
        RecordingCanceled=False
        self.plot_p = LinePlot(line_width=1.1, color=[1, 0, 0, 1])
        self.plot_f = LinePlot(line_width=1.1, color=[0.5, 1, 0.5, 1])
        self.plot_v = LinePlot(line_width=1.1, color=[0, 0.55, 0.8, 1])
        self.parameters = VentilatorParams()
        Clock.schedule_interval(self.update,refreshRate)

    def update(self, *args):
        global Recording,RecordingCanceled,ix, record_time,t_start,Sampleproc
        if self.EnableRecord: 
            if Recording:
                self.ids['grabar'].background_color = VERDE
                self.ids['grabar'].text = str(record_time - datetime.datetime.now())[2:7]
                if (record_time - datetime.datetime.now()) < datetime.timedelta(0):
                    os.killpg(os.getpgid(Sampleproc.pid), 15)
                    Recording=False 
                    self.EnableRecord = False
            if RecordingCanceled:
                self.EnableRecord = False
                RecordingCanceled=False
        else:
            self.ids['grabar'].text = "Grabación"
            self.ids['grabar'].background_color = NEGRO
            if self.EnableGraph:
                t_i=(datetime.datetime.now()-t_start).total_seconds()
                read=ads2.read_sequence(CH_SEQUENCE) * CH_GAIN/FILTER_SIZE
                for i in list(range(FILTER_SIZE -1)):
                    read+=ads2.read_sequence(CH_SEQUENCE) *  CH_GAIN/FILTER_SIZE
                t=(datetime.datetime.now()-t_start).total_seconds()
                if t>= 20:
                   self.plot_p.points.clear()
                   self.plot_f.points.clear()
                   self.plot_v.points.clear()
                   t_start = datetime.datetime.now()
                   t=t-t_i
                   t_i=0
                   self.parameters.time_last=0
                   self.parameters.state=None
                   
                self.parameters.time =(t+t_i)/2   
                self.parameters.pressure  =105.0/4.0*(read[1]-0.5) - 5.0
                self.parameters.flow =(-1)*(read[2]-2.5)*125.0
                self.parameters.oxygen=(39)*(read[0]-3.0) + 100.0
                self.parameters.defineState()
                self.parameters.calculateVolume()
                self.parameters.calculateFio2()
                self.parameters.calculatePIF()
                self.parameters.calculatePEF()
                self.parameters.calculateMaxPressure()
                self.parameters.calculateMinPressure()
                
                
        
                self.plot_p.points.append(( self.parameters.time, self.parameters.pressure))
                self.graph_P.add_plot(self.plot_p)

                self.plot_f.points.append(( self.parameters.time, self.parameters.flow))
                self.graph_F.add_plot(self.plot_f)

                self.plot_v.points.append(( self.parameters.time, self.parameters.volume))
                self.graph_V.add_plot(self.plot_v)

               
            if self.EnableShow:
                if self.parameters.NewStatsReady==1 :
                   self.pip_string = str(round(self.parameters.pip, 1))
                   self.peep_string = str(round(self.parameters.peep, 1))
                   self.ti_string = str(round(self.parameters.ti, 2))
                   self.fio2_string = str(round(self.parameters.fio2_mean, 1))
                   self.ie_string = str(round(self.parameters.ie, 1))
                   self.bpm_string = str(round(self.parameters.bpm, 1))
                   self.pif_string = str(round(self.parameters.pif, 1))
                   self.vti_string = str(int(self.parameters.vti))
                   self.parameters.statsReaded()
            else:
                self.pip_string = "--"
                self.peep_string = "--"
                self.ti_string= "--"
                self.fio2_string = "--"
                self.ie_string = "--"
                self.bpm_string = "--"
                self.pif_string = "--"
                self.vti_string = "--"

                


    def graphButton(self):
        global t_start,ads2,CH_GAIN
        if self.EnableGraph:
            self.ids['graficar'].background_color =NEGRO
            self.ids['mostrar'].background_color = NEGRO
            del ads2
            self.plot_p.points.clear()
            self.plot_f.points.clear()
            self.plot_v.points.clear()
            self.graph_P.add_plot(self.plot_p)
            self.graph_F.add_plot(self.plot_f)
            self.graph_V.add_plot(self.plot_v)
            self.EnableGraph = False
            self.EnableShow = False
            
        else:
            self.ids['graficar'].background_color = VERDE
            t_start=datetime.datetime.now()
            ads2 = ADS1256(myconfig_2)
            ads2.drate = DRATE_500  
            ads2.cal_self()
            chip_ID = ads2.chip_ID
            CH_GAIN = ads2.v_per_digit * GAIN_CAL
            self.EnableGraph = True
            
    def showButton(self):
        if self.EnableShow:
            self.ids['mostrar'].background_color =  NEGRO
            self.EnableShow = False
        elif self.EnableGraph:
            self.ids['mostrar'].background_color = VERDE
            self.EnableShow = True
        

    def recordButton(self):
       #if  self.EnableRecord:
           # self.ids['grabar'].background_color = (0.15, 0.15, 0.15, 1.0)
           # self.EnableRecord = False
            
        if not(self.EnableShow) and not(self.EnableGraph) and not(self.EnableRecord) :
            App.get_running_app().root.current = "record"
            self.manager.transition.direction = "down"
            self.EnableRecord = True
           

    def infoButton(self):
        if self.ids['info'].background_color == list(VERDE):
            self.ids['info'].background_color =  NEGRO
        elif self.ids['info'].background_color ==  list(NEGRO):
            self.ids['info'].background_color =  VERDE

    def exitButton(self):
        exit()

class MainApp(App):
    def build(self):
        pass

if __name__ == '__main__':
    MainApp().run()
