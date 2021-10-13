#!/usr/bin/python3
import datetime
from datetime import timedelta, timezone

import os
import numpy as np
from subprocess import Popen,PIPE
import time
from ventparams import VentilatorParams
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

from smbus2 import SMBus
I2C_ADDRESS=0x01
READ_TEMPERATURE_CMD=0xB2
READ_HUMIDITY_CMD=0xB3

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
Config.set('graphics', 'fullscreen', '1')
Config.set('graphics', 'show_cursor', '1')
Config.set('graphics', 'height', '480')
Config.set('graphics', 'width', '800')

Config.write()


record_time = ''
CSV_file_name = 'default'
count = 0
ix=0


refreshRate=1.0/25.0
FILTER_SIZE = 6



class WindowManager(ScreenManager):
    pass

class AdvertenciaPopUp(Popup):
    pass

class RecordWindow(Screen):
    file_name = ObjectProperty(None)
    min = ObjectProperty(None)
    sec = ObjectProperty(None)
    lugar= ObjectProperty(None)
    
    def accept(self):
        global Recording,RecordingCanceled, path,CSV_file_name, record_time,Sampleproc 
        print("spin text",self.lugar.text)
        print("spin",self.lugar.values)
        print(self.lugar.text+"/"+self.file_name.text)
        if(os.path.normpath(self.lugar.text+"/"+self.file_name.text)):
            if self.min.text.isnumeric()and int(self.min.text)<60:
                if self.sec.text.isnumeric()and int(self.sec.text)<60:
                    if(int(self.min.text)>0 or int(self.sec.text)>0):
                        record_time = datetime.datetime.now() + timedelta(minutes=int(self.min.text), seconds=int(self.sec.text))
                        if self.file_name.text != '':
                            path=self.lugar.text
                            CSV_file_name = self.file_name.text+'.csv'
                        Recording= True
                        Sampleproc = Popen("python3 sampler.py " + path+"/"+CSV_file_name,stdout=PIPE, stderr=PIPE, shell=True,preexec_fn=os.setsid)
                        App.get_running_app().root.current = "main"
                        self.manager.transition.direction = "up"
                    else:
                        AdvertenciaPopUp().open()   
                else:
                    AdvertenciaPopUp().open()  
            else:
                AdvertenciaPopUp().open()     
        else:
            AdvertenciaPopUp().open()
            
             
    def update_level_spinner(self):
        folderContents =os.listdir("/media/pi")
        folderContents.append("/home/pi/Desktop")
        values = folderContents
        values.sort()
        print(values)
        return values

    def cancel(self):
        global RecordingCanceled
        RecordingCanceled = True

class ClockText(Label):
    def __init__(self, *args, **kwargs):
        super(ClockText, self).__init__(*args, **kwargs)
        Clock.schedule_interval(self.update, 2)
       
    def update(self, *args):
        self.text = time.strftime('%I:%M:%S %p')
class TemHumText(Label):
    def __init__(self, *args, **kwargs):
        super(TemHumText, self).__init__(*args, **kwargs)
        Clock.schedule_interval(self.update, 10)
        self.temp=0
        self.hum=0
        time.sleep(0.01)
        self.readData()

    def update(self, *args):
        self.readData()
    def readData(self, *args):
        bus = SMBus(1)
        try:
            read = bus.read_byte_data(I2C_ADDRESS,READ_TEMPERATURE_CMD)
            temp=read<<8
            read = bus.read_byte_data(I2C_ADDRESS,READ_TEMPERATURE_CMD)
            self.temp=temp+read
            time.sleep(0.01)
            read = bus.read_byte_data(I2C_ADDRESS,READ_HUMIDITY_CMD)
            hum=read<<8
            read = bus.read_byte_data(I2C_ADDRESS,READ_HUMIDITY_CMD)
            self.hum=hum+read
        except IOError:
            print("error i2c")
        
        self.text = str(self.temp/100)+"°C "+str(self.hum/100)+" %"
class ConfigTab(TabbedPanel):
    pass
   

class MainWindow(Screen):
    
    graph_P = ObjectProperty(Graph())
    graph_F = ObjectProperty(Graph())
    graph_V = ObjectProperty(Graph())
    
    pip_string = StringProperty("--")
    peep_string = StringProperty("--")
    ti_string = StringProperty("--")
    te_string = StringProperty("--")
    fio2_string= StringProperty("--")
    ie_string = StringProperty("--")
    bpm_string = StringProperty("--")
    pif_string = StringProperty("--")
    pef_string = StringProperty("--")
    vti_string = StringProperty("--")
    vte_string = StringProperty("--")
    

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
        global Recording,RecordingCanceled,ix, path,record_time,t_start,Sampleproc,CSV_file_name
        if self.EnableRecord: 
            if Recording:
                self.ids['grabar'].background_color = VERDE
                self.ids['grabar'].text = str(record_time - datetime.datetime.now())[2:7]
                if (record_time - datetime.datetime.now()) < datetime.timedelta(0):
                    os.killpg(os.getpgid(Sampleproc.pid), 15)
                    Sampleproc = Popen("python3 computeStats.py " +CSV_file_name+" "+path,stdout=PIPE, stderr=PIPE, shell=True,preexec_fn=os.setsid)
                    Recording=False 
                    self.EnableRecord = False
            if RecordingCanceled:
                self.EnableRecord = False
                RecordingCanceled=False
        else:
            self.ids['grabar'].text = "Save"
            self.ids['grabar'].background_color = NEGRO
            if self.EnableGraph:
                t_i=(datetime.datetime.now()-t_start).total_seconds()
                read=ads2.read_sequence(CH_SEQUENCE) * CH_GAIN
                lecAnt=read
                lecAnt2=lecAnt
                lecturas=1
                for i in list(range(FILTER_SIZE -1)):
                    lec=ads2.read_sequence(CH_SEQUENCE) *  CH_GAIN
                    if(np.linalg.norm(lec-lecAnt2)<0.1):
                        read=read+lec
                        lecturas+=1
                    lecAnt2=lecAnt
                    lecAnt=lec
                read=read/lecturas   
                t=(datetime.datetime.now()-t_start).total_seconds()
                if t>= 20:
                   self.plot_p.points.clear()
                   self.plot_f.points.clear()
                   self.plot_v.points.clear()
                   t_start = datetime.datetime.now()
                   t=t-t_i
                   t_i=0
                  # self.parameters.time_last=0
                  # self.parameters.state=0
                   self.parameters = VentilatorParams()

                   
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
                   self.te_string = str(round(self.parameters.te, 2))
                   self.fio2_string = str(round(self.parameters.fio2_mean, 1))
                   self.ie_string = str(round(self.parameters.ie, 1))
                   self.bpm_string = str(round(self.parameters.bpm, 1))
                   self.pif_string = str(round(self.parameters.pif, 1))
                   self.pef_string = str(round(self.parameters.pef, 1))
                   self.vti_string = str(int(self.parameters.vti))
                   self.vte_string = str(int(self.parameters.vte))
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
            self.parameters = VentilatorParams()

    def showButton(self):
        if self.EnableShow:
            self.ids['mostrar'].background_color =  NEGRO
            self.EnableShow = False
        elif self.EnableGraph:
            self.ids['mostrar'].background_color = VERDE
            self.EnableShow = True
        

    def recordButton(self):
                  
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
