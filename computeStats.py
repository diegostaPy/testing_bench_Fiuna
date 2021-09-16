#!/usr/bin/env python
# coding: utf-8

# In[140]:


import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import integrate
from scipy import signal
import seaborn as sns
from matplotlib.ticker import StrMethodFormatter,ScalarFormatter,AutoMinorLocator
from scipy import integrate

SMALL_SIZE = 16
MEDIUM_SIZE = 18
BIGGER_SIZE = 20

plt.rc('font', size=SMALL_SIZE)          # controls default text sizes
plt.rc('axes', titlesize=SMALL_SIZE)     # fontsize of the axes title
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('legend', fontsize=SMALL_SIZE)    # legend fontsize
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title


# In[141]:


pruebasResumen=pd.DataFrame(columns=['n', 'C', 'R', 'setV', 'setIE', 'setBPM', 'setPEEP', 'setOxygen','prueba','setTi','setTe'])


# In[142]:


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


# In[143]:



dfBanco=pd.DataFrame(columns=['time', ' pressure', ' flow','n','prueba'])
dfBancoStats=pd.DataFrame(columns=['n','prueba', 'Ti s', 'Te s','Vti l','Vte l', 'I:E  ', 'BPM  ','PIP cmH2O','PEEP cmH2O','PIF lmin'])

df=pd.DataFrame(columns=[ 'Ti s', 'Te s', 'TiH s', 'TeH s', 'I:E  ', 'BPM  ',
'PIF lmin', 'PEF lmin', 'Vti l', 'Vte l', 'MV l', 'PIP cmH2O',
'IPP cmH2O', 'MAP cmH2O', 'PEEP cmH2O', 'Oxygen %', 'CMPL ml/cmH2O','prueba'])
j=0
k=0
xls = pd.ExcelFile('PruebasRealizadas.xlsx')
for name in xls.sheet_names:
    print(name)
    setValues = xls.parse(name)
    print(len(setValues))
    
   # setValues=setValues.drop('Unnamed: 8',axis=1)
   # setValues=setValues.iloc[:,0:8] 
    setValues['prueba']=name
    Tt=1/(setValues.setBPM.values/60.0)
    setValues['setTi']=Tt/(1+1/setValues.setIE.values)
    setValues['setTe']=setValues.setTi.values/setValues.setIE.values
    pruebasResumen=pd.concat([pruebasResumen, setValues], axis=0)
    
    j=j+1
    archivo='LecturaVt650/Banco'+name+'2.xlsx'
    if(os.path.exists(archivo)):
 xlsPrueba = pd.ExcelFile( archivo)
 i=0
 
 for pruebaName in  xlsPrueba.sheet_names[::-1]:
     if(pruebaName[0]=='R'):
         medidas = xlsPrueba.parse(pruebaName,skiprows=1)

         if(len(medidas.columns)>10  and len(medidas)>100):
             i=i+1
             ##VT650
             medidas.rename(columns = {'Unnamed: 0':'time'}, inplace = True)
            # medidas=medidas.drop('Unnamed: 0',axis=1)
             medidas['n']=int(i)
             
             medidas['prueba']=name
             medidas=medidas[12:]
             df = pd.concat([df, medidas], axis=0)
             
             ##Banco
             archivo='LecturaBanco/27_04new/banco2'+name+str(i)+'.csv'
             medidas=pd.read_csv(archivo)
             medidas['n']=int(i+1)
             medidas['prueba']=name
             medidas['time']=medidas['time'].values-medidas['time'].values[0]
            # medidas=medidas[medidas.time.values]
             medidas.loc[medidas[' flow'].values>100,' flow']=100
             medidas.loc[medidas[' flow'].values<-100,' flow']=-100
             
             medidas.set_index(["time"],drop=True, inplace=True)
             medidas['time']=medidas.index.values


             medidas['flow_mlpf']=signal.medfilt(medidas[' flow'].values,  11)

             medidas['pressure_mlpf']=signal.medfilt(medidas[' pressure'].values, 1)

             medidas.index = pd.to_datetime( medidas.index, unit='s')
             medidas=medidas.resample("5ms").median()
             medidas = medidas.interpolate(method='linear').dropna()
             medidas.reset_index(inplace = True, drop = True)

            # medidas['flow_mlpf']=signal.medfilt(medidas[' flow'].values,  11)
             th_hi=1#0.5
             th_lo=-1#-0.1
             cross= hyst(medidas['flow_mlpf'].values, th_lo, th_hi)
             Ti_ini=np.where(np.diff(cross*2-1,1)>0)[0]

             Ti_end=np.where(np.diff(cross*2-1,1)<0)[0]
             #Ti_ini=np.where(np.logical_and(np.logical_and(np.diff(np.concatenate(([0], np.logical_or(x >= th_hi,x <= th_lo)))),x >= th_hi),np.diff(np.concatenate(([0],medidas['pressure_mlpf'])))<0))[0]
             #Ti_end=np.where(np.logical_and(np.logical_and(np.diff(np.concatenate(([0], np.logical_or(x >= th_hi,x <= th_lo)))),x<th_lo),np.diff(np.concatenate(([0],medidas['pressure_mlpf'])))>0))[0]
             Ti_end=Ti_end[Ti_end>0]
             if(Ti_ini[0]>Ti_end[0]):
                 Ti_end=Ti_end[1:]
             ki=k
             medidas['volumen_mlpf']=np.zeros_like(medidas['flow_mlpf'].values)
             for ini,end,next_ini in zip(Ti_ini[:-1].tolist(),Ti_end[:-1].tolist(),Ti_ini[1:-1].tolist()):
                 medidas.loc[medidas.index.values[ini:next_ini],'volumen_mlpf']= np.hstack((np.array(0),integrate.cumtrapz(medidas['flow_mlpf'].values[ini:next_ini]/60, medidas.time.values[ini:next_ini])))
                 if(end<ini ):
                     continue
                 Tt= medidas.time.values[next_ini]-medidas.time.values[ini]
                 dfBancoStats.append(pd.Series(), ignore_index=True)
                 dfBancoStats.loc[k,'n']=int(i)
                 dfBancoStats.loc[k,'time']=medidas.time.values[ini]

                 dfBancoStats.loc[k,'prueba']=name
                 dfBancoStats.loc[k,'BPM  ']=(60.0/ Tt).astype(float)
                 dfBancoStats.loc[k,'Ti s']=(medidas.time.values[end]-medidas.time.values[ini]).astype(float)
                 dfBancoStats.loc[k,'Te s']=(medidas.time.values[next_ini]-medidas.time.values[end]).astype(float)
                 dfBancoStats.loc[k,'I:E  ']= (dfBancoStats.loc[k,'Ti s']/dfBancoStats.loc[k,'Te s']).astype(float)
                 dfBancoStats.loc[k,'PIP cmH2O']=(medidas.pressure_mlpf.values[ini:next_ini].max()).astype(float)
                 dfBancoStats.loc[k,'PEEP cmH2O']=(medidas.pressure_mlpf.values[end:next_ini].min()).astype(float)
                 dfBancoStats.loc[k,'PIF lmin']=(medidas.flow_mlpf.values[ini:next_ini].max()).astype(float)
                 dfBancoStats.loc[k,'Vti l']=(integrate.simps(medidas['flow_mlpf'].values[ini:(end-1)]/60, medidas.time.values[ini:(end-1)])).astype(float)
                 dfBancoStats.loc[k,'Vte l']=(integrate.simps(medidas['flow_mlpf'].values[end:next_ini]/60, medidas.time.values[end:next_ini]) ).astype(float) 
                 k=k+1
             print(str(k-ki))
             
             medidas.set_index(["time"],drop=True, inplace=True)

             dfBanco= pd.concat([dfBanco, medidas], axis=0)
           
             


# In[144]:


pruebasResumen=pruebasResumen.reset_index(drop=True)
pruebasResumenBK=pruebasResumen.copy()


# In[145]:


pruebasResumenBK.head()


# In[146]:


pruebasResumen=pruebasResumenBK.copy()


# In[147]:




variables=['Ti s', 'Te s','Vti l', 'I:E  ', 'BPM  ','PIP cmH2O','PEEP cmH2O','PIF lmin']
for prueba in ['Volumen', 'PEEP','Flujo', 'Frecuencia', 'InvFrecuencia']:
    pru=pruebasResumen[pruebasResumen['prueba']==prueba]
    for nn in np.unique(pru.n.values):
        vt=df[np.logical_and(df['n']==int(nn),df['prueba']==prueba)]
        banco=dfBancoStats[np.logical_and(dfBancoStats['n']==int(nn),dfBancoStats['prueba']==prueba)]
        if(True):
            pos=np.logical_and(pruebasResumen.n.values==int(nn),pruebasResumen.prueba.values==prueba)
            index=np.where(pos)[0][0]
            print(index)
            if(index==0):
                    pruebasResumen=pd.concat([pruebasResumen,pd.DataFrame(columns=['CiclosVt', 'RegistrosVt'])],axis=1)
                    pruebasResumen=pd.concat([pruebasResumen,pd.DataFrame(columns=['CiclosBanco', 'RegistrosBanco'])],axis=1)
            pruebasResumen.loc[index,'RegistrosVt']=len(vt)
            pruebasResumen.loc[index,'CiclosVt']=len(vt)/(60/int((pruebasResumen.loc[index,'setBPM'])))
            pruebasResumen.loc[index,'RegistrosBanco']=len(banco)
            pruebasResumen.loc[index,'CiclosBanco']=len(banco)/(60/int((pruebasResumen.loc[index,'setBPM'])))
            
            for var in variables:
                if(index==0):
                    pruebasResumen['vt'+var+'_min']=''
                    pruebasResumen['vt'+var+'_mean']=''
                    pruebasResumen['vt'+var+'_max']=''
                    pruebasResumen['banco'+var+'_min']=''
                    pruebasResumen['banco'+var+'_mean']=''
                    pruebasResumen['banco'+var+'_max']=''
                  
                pruebasResumen.loc[index,'vt'+var+'_min']=np.min(vt[var].values)
                pruebasResumen.loc[index,'vt'+var+'_mean']=np.mean(vt[var].values)
                pruebasResumen.loc[index,'vt'+var+'_max']=np.max(vt[var].values)
                
                pruebasResumen.loc[index,'banco'+var+'_min']=np.min(banco[var].values)
                pruebasResumen.loc[index,'banco'+var+'_mean']=np.mean(banco[var].values)
                pruebasResumen.loc[index,'banco'+var+'_max']=np.max(banco[var].values)
                
    
  
                


# In[148]:


pruebasResumen.to_csv('PruebasResumen.csv')


# In[149]:


pruebasResumen.head(100)


# In[157]:


lista=['Vti l', 'I:E  ', 'BPM  ','PEEP cmH2O','PIP cmH2O','PIF lmin']
label=['$V_{ti}(l)$','I:E','BPM','PEEP(cm$H_{2}O$)','PIP(cm$H_{2}O$)','PIF(l/min)']
setvalues=['setV','setIE','setBPM','setPEEP','NA','NA']
vt=pd.DataFrame(columns=lista)

banco=pd.DataFrame(columns=lista)

MeanError=pd.DataFrame(columns=lista)
StdError=pd.DataFrame(columns=lista)
i=0
fig= plt.figure(figsize=(20,30))
plt.subplots_adjust( hspace=0.4 ) 
k=-1
for prueba, pb in zip([ 'Volumen', 'PEEP','Flujo','Frecuencia'],[ '$V_{t}$', 'PEEP','BPM,$V_{t}$','BPM']):
    dd=df[df['prueba']==prueba]
    #fig.suptitle('Prueba  '+" Resistencia="+str(pruebasResumen.loc[index,'R'])+"(cm$H_{2}O$/l/s ) Complianza="+str(pruebasResumen.loc[index,'C'])+" (ml/cm$H_{2}O$ )",y=0.95)
    print(prueba)
    
    for nn in np.unique(dd.n.values):
        print(nn)
        pos=np.logical_and(pruebasResumen.n.values==int(nn),pruebasResumen.prueba.values==prueba)
        index=np.where(pos)[0][0]
        k=k+1
        MeanError.loc[k]=0.0
        StdError.loc[k]=0.0
        for var,lb,setval in zip(lista,label,setvalues):
            dff=dd[dd['n']==nn]
            dffBanco=dfBancoStats[np.logical_and(dfBancoStats.n.values==int(nn),dfBancoStats.prueba.values==prueba)]
            
            xmin=np.min(dff[var].values)*0.98
            xmax=np.max(dff[var].values)*1.02
            xmin=min(xmin,np.min(dffBanco[var].values)*0.98)
            xmax=max(xmax,np.max(dffBanco[var].values)*1.02)
            
            dffBanco.set_index(["time"],drop=True, inplace=True)
            dffBanco.index = pd.to_datetime( dffBanco.index, unit='s')
            dffBanco.index =dffBanco.index-dffBanco.index[0] 
            dffBanco=dffBanco.drop('prueba',axis=1)
            s = dffBanco.select_dtypes(include='object').columns
            dffBanco[s] = dffBanco[s].astype("float")
            dffBanco.resample('s').interpolate()
            dff.set_index(["time"],drop=True, inplace=True)
            dff.index = pd.to_datetime( dff.index,format='%H:%M:%S')
            dff.index =dff.index-dff.index[0] 
            dff=dff.drop('prueba',axis=1)

            s = dff.select_dtypes(include='object').columns
            dff[s] = dff[s].astype("float")
            
            combined = pd.merge_asof(dff,dffBanco ,on='time')
            
            
            #print(var)
            #print('mean')
            ##print(str(np.mean(combined[var+'_x'].values-combined[var+'_y'].values)))
            #print('std')
            #print(str(np.std(combined[var+'_x'].values-combined[var+'_y'].values)))

            i=i+1
            axes=plt.subplot(11,len(lista),i)
            axe=sns.scatterplot(x=var+'_x',y=var+'_y',data=combined, color="r",alpha=0.5, linewidth=0.3)
            error="%.3f"%np.mean((combined[var+'_x'].values-combined[var+'_y'].values))
            error+=u"\u00B1"
            error+=" %.3f"%np.std((combined[var+'_x'].values-combined[var+'_y'].values))
            #error+=" "+unit
           
            MeanError[var].loc[k]=np.mean((combined[var+'_x'].values-combined[var+'_y'].values))
            

            StdError[var].loc[k]=np.std((combined[var+'_x'].values-combined[var+'_y'].values))
            
            vt[var].loc[k]=np.mean(combined[var+'_y'].values)
            banco[var].loc[k]=np.mean(combined[var+'_y'].values)
           
            axe.text(xmin+(xmax-xmin)*0.1, xmin+(xmax-xmin)*0.8, error, size=16, color='blue')
            plt.plot([xmin, xmax], [xmin, xmax], linewidth=2, color="black",alpha=0.5)
            #
            #sns.stripplot(x=var,data=dff,size=4, color="r",alpha=0.5, linewidth=0.3)
            #sns.stripplot(x=var,data=dffBanco,size=4, color="g",alpha=0.5, linewidth=0.3)
            #sns.violinplot(x=var,data=dff, width=1)
           # sns.stripplot(x=var,data=dff,size=4, color=".3", linewidth=0)
            #if (nn==1):
            axes.set_xlabel('')
           
            axes.set_title(lb)
            if(var=='Vti l'):
                axes.set_ylabel(pb+' n='+str(int(nn))) 
            else:
                axes.set_ylabel('') 

            axes.set_xlim(xmin, xmax)
            axes.set_ylim(xmin, xmax)
            formatter = ScalarFormatter(useOffset=False)
            axes.yaxis.set_major_formatter(formatter)
            axes.yaxis.set_minor_locator(AutoMinorLocator(5))
            axes.xaxis.set_major_formatter(formatter)
            axes.xaxis.set_minor_locator(AutoMinorLocator(5))
       
            
           # plt.yticks([], [])
plt.tight_layout(rect=[0, 0.03, 1.001, 0.95])
plt.savefig(prueba+'_APPBB.png', dpi=300)
plt.show()
    


# In[159]:


MeanError.head()


# In[168]:


MeanError.describe()


# In[169]:


StdError.describe()


# In[160]:


lista=['Vti l', 'I:E  ', 'BPM  ','PEEP cmH2O','PIP cmH2O','PIF lmin','Ti s', 'Te s',]
label=['$V_{ti}$','I:E','BPM','PEEP(cm$H_{2}O$)','PIP(cm$H_{2}O$)','PIF(lmin)','$T_{i}$', '$T_{e}$']
setvalues=['setV','setIE','setBPM','setPEEP','NA','NA','setTi','setTe']

vt=pd.DataFrame(columns=lista)
banco=pd.DataFrame(columns=lista)
MeanError=pd.DataFrame(columns=lista)
StdError=pd.DataFrame(columns=lista)
i=0
k=-1
for prueba in [ 'Volumen', 'PEEP','Flujo']:
    dd=df[df['prueba']==prueba]
    for nn in np.unique(dd.n.values):
        print(nn)
        pos=np.logical_and(pruebasResumen.n.values==int(nn),pruebasResumen.prueba.values==prueba)
        index=np.where(pos)[0][0]
        k=k+1
        MeanError.loc[k]=0.0
        StdError.loc[k]=0.0
        vt.loc[k]=0.0
        banco.loc[k]=0.0
        for var in lista:
            dff=dd[dd['n']==nn]
            dffBanco=dfBancoStats[np.logical_and(dfBancoStats.n.values==int(nn),dfBancoStats.prueba.values==prueba)]
            
            dffBanco.set_index(["time"],drop=True, inplace=True)
            dffBanco.index = pd.to_datetime( dffBanco.index, unit='s')
            dffBanco.index =dffBanco.index-dffBanco.index[0] 
            dffBanco=dffBanco.drop('prueba',axis=1)
            s = dffBanco.select_dtypes(include='object').columns
            dffBanco[s] = dffBanco[s].astype("float")
            dffBanco.resample('s').interpolate()
            dff.set_index(["time"],drop=True, inplace=True)
            dff.index = pd.to_datetime( dff.index,format='%H:%M:%S')
            dff.index =dff.index-dff.index[0] 
            dff=dff.drop('prueba',axis=1)

            s = dff.select_dtypes(include='object').columns
            dff[s] = dff[s].astype("float")
            
            combined = pd.merge_asof(dff,dffBanco ,on='time')
            
          
            i=i+1
            error="%.3f"%np.mean((combined[var+'_x'].values-combined[var+'_y'].values))
            error+=u"\u00B1"
            error+=" %.3f"%np.std((combined[var+'_x'].values-combined[var+'_y'].values))
            MeanError[var].loc[k]=np.mean((combined[var+'_x'].values-combined[var+'_y'].values))
            StdError[var].loc[k]=np.std((combined[var+'_x'].values-combined[var+'_y'].values))
            vt[var].loc[k]=np.mean(combined[var+'_x'].values)
            banco[var].loc[k]=np.mean(combined[var+'_y'].values)
           


# In[161]:


vt.head()


# In[162]:


fig, ax = plt.subplots(figsize=(7,7))

ax.errorbar(1000*vt['Vti l'],1000*banco['Vti l'], yerr=10000*StdError['Vti l'], color='red', ls='', marker='o', capsize=5, capthick=1, ecolor='black')
plt.plot([150, 500], [150, 500], linewidth=2, color="black",alpha=0.5)
ax.set_title('Tidal Volume')
ax.set_ylabel(' Pytu Test Bench (mL)') 
ax.set_xlabel(' Gas Flow Analyzer  Fluke VT650') 
#ax.set_xlim(xlims)
#ax.set_ylim(ylims)


# In[165]:


lista=['Vti l', 'I:E  ', 'BPM  ','PEEP cmH2O','PIP cmH2O','PIF lmin','Ti s', 'Te s',]
label=['$V_{ti}$','I:E','BPM','PEEP(cm$H_{2}O$)','PIP(cm$H_{2}O$)','PIF(lmin)','$T_{i}$', '$T_{e}$']
title=['Tidal Volume (mL)','I:E','BPM','PEEP(cm$H_{2}O$)','PIP(cm$H_{2}O$)','PIF(mL/min)','$T_{i} (s)$', '$T_{e} (s)$']
scale=[1000,10,10,10,10,10,10,10]
file=['vol','ie','bpm','peep','pip','pif','ti', 'te']

for var,lab,ti,sca,fil in zip(lista,label,title, scale,file):
    fig, ax = plt.subplots(figsize=(7,7))
    x=sca*vt[var].values
    y=sca*banco[var].values
    yerr=sca*StdError[var].values
    
    ax.errorbar(x,y, yerr=yerr,color='red', ls='', marker='o', capsize=5, capthick=1,ecolor='black')
    xmin=np.min(x)*0.98
    xmax=np.max(x)*1.02
    xmin=min(xmin,np.min(y)*0.98)
    xmax=max(xmax,np.max(y)*1.02)
            
                   
                   
    plt.plot([xmin, xmax], [xmin, xmax], linewidth=1, color="black",alpha=0.8)
    ax.set_title(ti)
    ax.set_ylabel(' Pytu Test Bench') 
    ax.set_xlabel(' Gas Flow Analyzer  Fluke VT650')
    #plt.savefig(fil+'_A.png', dpi=300)

#ax.set_xlim(xlims)
#ax.set_ylim(ylims)


# In[164]:


lista=['Vti l', 'I:E  ', 'BPM  ','PEEP cmH2O','PIP cmH2O','PIF lmin','Ti s', 'Te s',]
label=['$V_{ti}$','I:E','BPM','PEEP(cm$H_{2}O$)','PIP(cm$H_{2}O$)','PIF(lmin)','$T_{i}$', '$T_{e}$']
setvalues=['setV','setIE','setBPM','setPEEP','NA','NA','setTi','setTe']
i=0
fig= plt.figure(figsize=(20,15))
fig.suptitle('Prueba '+" Resistencia="+str(pruebasResumen.loc[index,'R'])+"(cm$H_{2}O$/l/s ) Complianza="+str(pruebasResumen.loc[index,'C'])+" (ml/cm$H_{2}O$ )",y=0.95)
plt.subplots_adjust( hspace=0.4 ) 

for prueba in [ 'Frecuencia', 'InvFrecuencia']:
    dd=df[df['prueba']==prueba]
    print(prueba)
    for nn in np.unique(dd.n.values):
        pos=np.logical_and(pruebasResumen.n.values==int(nn),pruebasResumen.prueba.values==prueba)
        index=np.where(pos)[0][0]
        print(nn)
        for var,lb,setval in zip(lista,label,setvalues):
            dff=dd[dd['n']==nn]
            dffBanco=dfBancoStats[np.logical_and(dfBancoStats.n.values==int(nn),dfBancoStats.prueba.values==prueba)]
            
            xmin=np.min(dff[var].values)*0.95
            xmax=np.max(dff[var].values)*1.05
            xmin=min(xmin,np.min(dffBanco[var].values)*0.95)
            xmax=max(xmax,np.max(dffBanco[var].values)*1.05)
            
            
            dffBanco.set_index(["time"],drop=True, inplace=True)
            dffBanco.index = pd.to_datetime( dffBanco.index, unit='s')
            dffBanco.index =dffBanco.index-dffBanco.index[0] 
            dffBanco=dffBanco.drop('prueba',axis=1)
            s = dffBanco.select_dtypes(include='object').columns
            dffBanco[s] = dffBanco[s].astype("float")
            dffBanco.resample('s').interpolate()
            dff.set_index(["time"],drop=True, inplace=True)
            dff.index = pd.to_datetime( dff.index,format='%H:%M:%S')
            dff.index =dff.index-dff.index[0] 
            dff=dff.drop('prueba',axis=1)

            s = dff.select_dtypes(include='object').columns
            dff[s] = dff[s].astype("float")
            
            combined = pd.merge_asof(dff,dffBanco ,on='time')
            print(var)
            print('mean')
            print(str(np.mean(combined[var+'_x'].values-combined[var+'_y'].values)))
            print('std')
            print(str(np.std(combined[var+'_x'].values-combined[var+'_y'].values)))

            i=i+1
            axes=plt.subplot(4,len(lista),i)
            sns.scatterplot(x=var+'_x',y=var+'_y',data=combined, color="r",alpha=0.5, linewidth=0.3)
            plt.plot([xmin, xmax], [xmin, xmax], linewidth=2, color="black",alpha=0.5)

          #  sns.stripplot(x=var,data=dff,size=4, color="r", linewidth=0)
          #  sns.stripplot(x=var,data=dffBanco,size=4, color="g",alpha=0.5, linewidth=0)
                   #sns.violinplot(x=var,data=dff, width=1)
           # sns.stripplot(x=var,data=dff,size=4, color=".3", linewidth=0)
            #if (nn==1):
            axes.set_xlabel('')
           
            axes.set_title(lb)
            if(var=='Vti l'):
                axes.set_ylabel(prueba+' n='+str(int(nn))) 
            else:
                axes.set_ylabel('') 

            axes.set_xlim(xmin, xmax)
            axes.set_ylim(xmin, xmax)
            formatter = ScalarFormatter(useOffset=False)
            axes.yaxis.set_major_formatter(formatter)
            axes.yaxis.set_minor_locator(AutoMinorLocator(5))
            axes.xaxis.set_major_formatter(formatter)
            axes.xaxis.set_minor_locator(AutoMinorLocator(5))
plt.tight_layout(rect=[0, 0.03, 1.001, 0.95])
#plt.savefig(prueba+'_BPP.png', dpi=300)
plt.show()
    


# In[ ]:





# In[ ]:





# In[ ]:


dfBancoStats.head()


# In[35]:


dfBancoStats.info()


# In[ ]:




