#!/usr/bin/env python3

import sys
import pandas as pd
import numpy as np
from scipy import integrate
from scipy import signal
fs=80
cutoff=5
lpf=signal.firwin(40, cutoff/fs, window='hamming')

def hyst(x, th_lo, th_hi, initial = False):
    hi = x >= th_hi
    lo_or_hi = (x <= th_lo) | hi
    ind = np.nonzero(lo_or_hi)[0]
    if not ind.size: # prevent index error if ind is empty
        return np.zeros_like(x, dtype=bool) | initial
    cnt = np.cumsum(lo_or_hi) # from 0 to len(x)
    return np.where(cnt, hi[ind[cnt-1]], initial)   

filename = sys.argv[1]
path= sys.argv[2]


medidas=pd.read_csv(path+"/"+filename,comment="#",names=['time', ' pressure',' flow','fio2'],skiprows=2)
print(medidas[0])
medidas['time']=medidas['time'].values-medidas['time'].values[0]
medidas.loc[medidas[' flow'].values>100,' flow']=100
medidas.loc[medidas[' flow'].values<-100,' flow']=-100
medidas.set_index(["time"],drop=True, inplace=True)
medidas['time']=medidas.index.values
medidas['flow_mlpfE']=medidas[' flow'].values
medidas['flow_mlpfE']=signal.medfilt(medidas['flow_mlpfE'].values,11)
flaP=medidas['flow_mlpfE'].values>5
flaN=medidas['flow_mlpfE'].values<-15
medidas['flow_mlpf']=medidas['flow_mlpfE']
medidas['flow_mlpf'][flaP]=2.17444+medidas['flow_mlpf'][flaP]*  0.908218
medidas['flow_mlpf'][flaN]= -1.356572+medidas['flow_mlpf'][flaN]*   1.068238
medidas['flow_mlpf']=signal.convolve(medidas['flow_mlpf'].values, lpf, mode='same')
medidas['pressure_mlpf']=signal.medfilt(medidas[' pressure'].values, 5)
medidas.index = pd.to_datetime( medidas.index, unit='s')
medidas=medidas.resample("2.5ms").median()
medidas = medidas.interpolate(method='linear').dropna()
medidas.reset_index(inplace = True, drop = True)

th_hi=5#0.5
th_lo=-5#-0.1
cross= hyst(medidas['flow_mlpf'].values, th_lo, th_hi)
Ti_ini=np.where(np.diff(cross*2-1,1)>0)[0]
Ti_ini=Ti_ini[Ti_ini>250]
Ti_end=np.where(np.diff(cross*2-1,1)<0)[0]
Ti_end=Ti_end[Ti_end>250]
Ti_end=Ti_end[Ti_end>0]
if(len(Ti_end)==0 or len(Ti_ini)==0):
    print("no hay datos")
    exit()
if(Ti_ini[0]>Ti_end[0]):
    Ti_end=Ti_end[1:]
k=0
medidas['volumen_mlpf']=np.zeros_like(medidas['flow_mlpf'].values)
dfBancoStats=pd.DataFrame(columns=['Ti s', 'Te s','Vti l','Vte l', 'I:E  ', 'BPM  ','PIP cmH2O','PEEP cmH2O','PIF lmin','PEF lmin','FiO2mean','FiO2min','FiO2max'])
print("tenemos N registros")
print(len(T_ini))
for ini,end,next_ini,kk in zip(Ti_ini[:-1].tolist(),Ti_end[:-1].tolist(),Ti_ini[1:-1].tolist(),np.arange(len(Ti_end[:-1]))):
    ini=ini-250+np.where(medidas.flow_mlpf.values[ini-250:ini]>0.1)[0][0]
    next_ini=next_ini-250+np.where(medidas.flow_mlpf.values[next_ini-250:next_ini]>0.1)[0][0]
    Ti_ini[kk]=ini
    end=end-100+np.where(medidas.flow_mlpf.values[end-100:end]<0)[0][0]
    Ti_end[kk]=end
    medidas.loc[medidas.index.values[ini:next_ini],'volumen_mlpf']= np.hstack((np.array(0),integrate.cumtrapz(medidas['flow_mlpf'].values[ini:next_ini]/60, medidas.time.values[ini:next_ini])))
    if(end<ini ):
        continue
    if(end>next_ini ):
        continue
    if((end-ini)<250):
        continue
    Tt= medidas.time.values[next_ini]-medidas.time.values[ini]
    dfBancoStats.append(pd.Series(), ignore_index=True)

    dfBancoStats.loc[k,'time']=medidas.time.values[ini]

    dfBancoStats.loc[k,'BPM  ']=(60.0/ Tt).astype(float)
    dfBancoStats.loc[k,'Ti s']=(medidas.time.values[end]-medidas.time.values[ini]).astype(float)
    dfBancoStats.loc[k,'Te s']=(medidas.time.values[next_ini]-medidas.time.values[end]).astype(float)
    dfBancoStats.loc[k,'I:E  ']= (dfBancoStats.loc[k,'Ti s']/dfBancoStats.loc[k,'Te s']).astype(float)
    dfBancoStats.loc[k,'PIP cmH2O']=(medidas.pressure_mlpf.values[ini:next_ini].max()).astype(float)
    dfBancoStats.loc[k,'PEEP cmH2O']=(medidas.pressure_mlpf.values[end:next_ini].min()).astype(float)
    dfBancoStats.loc[k,'PIF lmin']=(medidas.flow_mlpf.values[ini:next_ini].max()).astype(float)
    dfBancoStats.loc[k,'PEF lmin']=-(medidas.flow_mlpf.values[end:next_ini].min()).astype(float)
    dfBancoStats.loc[k,'Vti l']=(integrate.simps(medidas['flow_mlpf'].values[ini:(end-1)]/60, medidas.time.values[ini:(end-1)])).astype(float)
    dfBancoStats.loc[k,'Vte l']=-(integrate.simps(medidas['flow_mlpf'].values[end:next_ini]/60, medidas.time.values[end:next_ini]) ).astype(float) 
    dfBancoStats.loc[k,'FiO2mean']=(medidas.fio2.values[ini:next_ini].mean()).astype(float)
    dfBancoStats.loc[k,'FiO2min']=(medidas.fio2.values[ini:next_ini].min()).astype(float)
    dfBancoStats.loc[k,'FiO2max']=(medidas.fio2.values[ini:next_ini].max()).astype(float)

    k=k+1
print("listo")
dfBancoStats.to_csv(path+"/"+"stats_"+filename)             
    




