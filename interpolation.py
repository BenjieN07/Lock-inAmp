# -*- coding: utf-8 -*-
"""
Created on Tue Jul 17 12:36:33 2018

@author: MOKE
"""

import glob
import os.path as op
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import griddata



def getData(wnum_start, wnum_stop, wnum_prec, curr_prec, step, folder):
    '''
    wnum_start : int or float
        The smallest wavenumber in the data from the scan
    wnum_stop : int or float
        The largest wavenumber in the data from the scan
    wnum_prec : int or float
        The precision of the wavenumber (number of decimal places)
        0 implies no decimal places
        Cannot be negative
        Ex. 1089.90 cm^-1 would have a wnum_prec of 2
    curr_prec : int or float
        The precision of the wavenumber (number of decimal places)
        0 implies no decimal places
        Cannot be negative
        Ex. 1378 mA would have a curr_prec of 0
    step : int or float
        The wavenumber step or wavenumber resolution used during the scan
    folder : str
        Name of the folder within the data folder (should make a separate folder
        for each intrument))
    '''
    df = pd.DataFrame({'Time' : [], 'Power' : [], 'Wavenumber' : [], 'Current' : []}) #make empty dataframe
    
    # get start and end current float values
    clist = glob.glob(folder +'/*mA.txt')
    
    clist.sort(key=lambda x:int(op.basename(x).rstrip('mA.txt')))
    curr_start = float(op.basename(clist[0]).rstrip('mA.txt'))
    curr_stop = float(op.basename(clist[-1]).rstrip('mA.txt'))
#     curr_start = float(clist[0].rstrip('mA.txt').lstrip('../Data/' + folder + '/'))
#     curr_stop = float(clist[-1].rstrip('mA.txt').lstrip('../Data/' + folder + '/'))
    
    for cur in clist:
        temp = pd.read_csv(cur, sep='\t', skiprows=36)
        temp = temp.drop(temp.index[[0]]) #drop the first row of data, since it is collected before the scan starts
        temp = temp.drop(temp.columns[2:], axis=1) #drop all columns except timestamp and channel A (power)
        
        wnums = np.arange(wnum_start, wnum_stop + step, step) #store wavenumbers, from wnum_start to wnum_stop inclusive
        temp = temp.assign(wnum=pd.Series(wnums, index=temp.index))
        
        current = int(op.basename(cur).rstrip('mA.txt'))
        currents = [current] * len(temp.index)
        temp = temp.assign(curr=pd.Series(currents, index = temp.index))
        
        
        temp.columns = ['Time', 'Power', 'Wavenumber', 'Current'] #change column names
        
        df = df.append(temp, ignore_index = True)
    
    df['Power'] *= 1e3 #convert to mW
    
    
    #prepare original data to produce a 2d color map
    orig_dat = df[['Current', 'Wavenumber', 'Power']]
    orig_dat = orig_dat.pivot('Current', 'Wavenumber', 'Power')
    
    #create interpolated data and prepare it to produce a 2d color map
    points = np.array(df[['Wavenumber', 'Current']])
    values = np.array(df['Power'])
    curr_step = 10**-curr_prec
    wnum_step = 10**-wnum_prec
    curr_inputs = np.arange(curr_start, curr_stop + curr_step, curr_step)
    wnum_inputs = np.arange(wnum_start, wnum_stop + wnum_step, wnum_step)
    xx, yy = np.mgrid[wnum_start:wnum_stop+wnum_step:wnum_step, curr_start:curr_stop+curr_step:curr_step]
    interp = griddata(points, values, (xx, yy), method='linear')
    curr_dat = np.repeat(curr_inputs, wnum_inputs.size)
    wnum_dat = np.tile(wnum_inputs, curr_inputs.size)
    model_dat = pd.DataFrame({'Current':curr_dat, 'Wavenumber':wnum_dat, 'Power':interp.T.flatten()})
    
    model_dat['Wavenumber'] = round(model_dat['Wavenumber'], wnum_prec)
    model_dat['Current'] = round(model_dat['Current'], curr_prec)
    
    if wnum_prec == 0:
        model_dat['Wavenumber'] = model_dat['Wavenumber'].astype(int)
    if curr_prec == 0:
        model_dat['Current'] = model_dat['Current'].astype(int)
        
    if wnum_prec < 0 or curr_prec < 0:
        raise ValueError('Precision must be a non-negative number')
    
    model_dat = model_dat.pivot('Current', 'Wavenumber', 'Power')
    
    return orig_dat, model_dat
    
def plotOrigData(orig_dat, cmap='magma'):
    i = orig_dat.index.values
    w = orig_dat.columns.values
    ww, ii = np.meshgrid(w, i)
    fig,ax = plt.subplots(1,1,figsize=(8,6))
    img = plt.pcolormesh(ww,ii,orig_dat,cmap=cmap)
    cbar = fig.colorbar(img)
    ax.set_xlabel('Wavenumber ($cm^{-1}$)')
    ax.set_ylabel('Current ($mA$)')
    ax.set_title('Wavenumber and Current vs Power ($mW$)')
    return fig, ax

def plotModelData(model_dat, cmap='magma'):
    i = model_dat.index.values
    w = model_dat.columns.values
    ww, ii = np.meshgrid(w, i)
    fig,ax = plt.subplots(1,1,figsize=(8,6))
    img = plt.pcolormesh(ww,ii,model_dat,cmap=cmap)
    cbar = fig.colorbar(img)
    ax.set_xlabel('Wavenumber ($cm^{-1}$)')
    ax.set_ylabel('Current ($mA$)')
    ax.set_title('Wavenumber and Current vs Power ($mW$) with Interpolation')
    return fig, ax

def plotAllData(orig_dat, model_dat, cmap='magma'):
    i_o = orig_dat.index.values
    w_o = orig_dat.columns.values
    ww_o, ii_o = np.meshgrid(w_o, i_o)
    
    i_m = model_dat.index.values
    w_m = model_dat.columns.values
    ww_m, ii_m = np.meshgrid(w_m, i_m)
    
    fig, (ax_o, ax_m) = plt.subplots(2,1,figsize=(8,12))
    
    img_o = ax_o.pcolormesh(ww_o,ii_o,orig_dat,cmap=cmap)
    fig.colorbar(img_o, ax=ax_o)
    ax_o.set_xlabel('Wavenumber ($cm^{-1}$)')
    ax_o.set_ylabel('Current ($mA$)')
    ax_o.set_title('Original Wavenumber and Current vs Power ($mW$)')
    
    img_m = ax_m.pcolormesh(ww_m,ii_m,model_dat,cmap=cmap)
    fig.colorbar(img_m, ax=ax_m)
    ax_m.set_xlabel('Wavenumber ($cm^{-1}$)')
    ax_m.set_ylabel('Current ($mA$)')
    ax_m.set_title('Interpolated Wavenumber and Current vs Power ($mW$)')
    
    fig.tight_layout()
    
    return fig, (ax_o, ax_m)

def constPower(wnum_start, wnum_stop, step, targetPwr, model_dat):
    wnum_vals = np.arange(wnum_start, wnum_stop + step, step) #array from start to stop inclusive
    curr_list = [] #list of currents to keep power constant
    
    for wnum in wnum_vals:
        curr = abs(model_dat[wnum] - targetPwr).idxmin()
        curr_list.append(curr)
    
    return wnum_vals, np.array(curr_list)

def plotInterpolation(ax, wnums, currs, c='g', linewidth=3):
    return ax.plot(wnums, currs, c='g', linewidth=3)
