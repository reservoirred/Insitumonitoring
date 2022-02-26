#%% usb camera test
import cv2
import matplotlib.pyplot as plt
import time
import numpy as np
from tkinter import filedialog
from tkinter import *
import os
import sys
import subprocess
import datetime
from datetime import datetime

import nidaqmx
from nidaqmx.stream_readers import AnalogMultiChannelReader
from nidaqmx import constants
import threading

import warnings
import pyautogui
warnings.simplefilter("ignore", ResourceWarning)

#%% functions

def start_infared():
    pyautogui.click(x=1400, y=250)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'r')
    time.sleep(0.2)
    pyautogui.click(x=1400, y=250)
    time.sleep(0.2)

def start_stop_infared():
    pyautogui.click(x=1400, y=250)
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'r')
    time.sleep(0.5)
    pyautogui.hotkey('ctrl', 'r')
    time.sleep(0.2)
    pyautogui.click(x=400, y=15)
    time.sleep(0.2)

def set_folder():      
    root = Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    folder_selected = filedialog.askdirectory(parent=root)
    return folder_selected

def detect_yellow():
    ret,frame = cap.read()
    b = frame[:, :, :1]
    g = frame[:, :, 1:2]
    r = frame[:, :, 2:]
 
    # computing the mean
    b_mean = np.mean(b)
    g_mean = np.mean(g)
    r_mean = np.mean(r)
    if b_mean<100:
        return True
    else:
        return False
   
def TakeNikonPicture(input_filename):
    camera_command = 'C:\Program Files (x86)\digiCamControl\CameraControlCmd.exe'
    camera_command_details = '/filename ' + input_filename + ' /capture /iso 2400 /shutter 1/300 /aperture 1.8'
    print('camera details = ',camera_command_details)
    full_command=camera_command + ' ' + camera_command_details
    p = subprocess.Popen(full_command, stdout=subprocess.PIPE, universal_newlines=True, shell=False)
    (output, err) = p.communicate()

def cfg_read_task(acquisition):
    acquisition.ai_channels.ai_gain = 100
    acquisition.ai_channels.ai_max = 100
    acquisition.ai_channels.add_ai_voltage_chan("cDAQ1Mod1/ai0",
                                              max_val=30,
                                              min_val=-30)
    acquisition.ai_channels.add_ai_voltage_chan("cDAQ1Mod1/ai1",
                                              max_val=30,
                                              min_val=-30)
    acquisition.ai_channels.add_ai_voltage_chan("cDAQ1Mod1/ai2",
                                              max_val=30,
                                              min_val=-30)
    # Cards1
    # acquisition.ai_channels.add_ai_accel_chan("cDAQ1Mod1/ai1",
    #                                           sensitivity=1000.0,
    #                                           max_val=1,
    #                                           min_val=-1)  # Cards2
    acquisition.timing.cfg_samp_clk_timing(rate=sampling_freq_in,
                                           sample_mode=constants.AcquisitionType.CONTINUOUS,
                                           samps_per_chan=buffer_in_size_cfg)

def reading_task_callback(task_idx, event_type, num_samples, callback_data):
    global data
    global buffer_in
    if running:
        #path = 'C:\\Users\\Beuth10\\Desktop\\Insitumonitoring_testing\\'
        path  = main_folder+'/acoustics/Layer'+str(layer_num).zfill(7)+'/'
        isExist = os.path.exists(path)
        if not isExist:
            os.makedirs(path)
        buffer_in = np.zeros((chans_in, num_samples))  # double definition ???
        stream_in.read_many_sample(buffer_in, num_samples,
                                   timeout=constants.WAIT_INFINITELY)
        data = np.append(data, buffer_in,
                         axis=1)  # appends buffered data to total variable data
        filename = path + 'Acc_' + str(
            datetime.now().strftime("%m%d%h%H%M%S%f"))
        extension = '.txt'
        np.savetxt(filename + extension, data)
        #plt.figure()
        #plt.plot(data)
        # f=np.fft.rfftfreq(data[4][1::].size,d=1/100000)
        # P=abs(np.fft.rfft(data[4][1::]))
        # plt.plot(f[f>200] ,P[f>200],'k')
        # plt.xlim(100,10000)
        # plt.plot(data[0][1::],'k--')
        data = np.zeros((chans_in, 1))
    return 0



#%% intialize
start_time = time.time()

# folders
main_folder = set_folder()
data_types = ['acoustics','optical','infared','layertimes']
for i in data_types:
    try:
        os.mkdir(main_folder+'/'+i)
    except:
        pass

# webcam
cap = cv2.VideoCapture(0)

# acoustic monitoring
    # Parameters
sampling_freq_in = 100000  # in Hz
buffer_in_size = 800000
bufsize_callback = 200000
buffer_in_size_cfg = round(buffer_in_size) * 10  # clock configuration * 10 ?
chans_in = 3  # number of chan
refresh_rate_plot = 100000  # in Hz
crop = 0  # number of seconds to drop at acquisition start before saving

# Initialize data placeholders
buffer_in = np.zeros((chans_in, buffer_in_size))
data = np.zeros(
    (chans_in, 1))

# nikon camera


#%% monitor
# initialize
recoater_pos = True
state_change = False
state_change_counts = 0
layer_num = 0
post_fusion_state = True

# start acoustic monitoring processes
task_in = nidaqmx.Task()
cfg_read_task(task_in)
stream_in = AnalogMultiChannelReader(task_in.in_stream)
task_in.register_every_n_samples_acquired_into_buffer_event(bufsize_callback,
                                                            reading_task_callback)
running = True
time_start = datetime.now()
task_in.start()
start_infared()

while True:
    # Check recoater state
    n_recoater_state = detect_yellow()
    if recoater_pos != n_recoater_state :
        recoater_pos = n_recoater_state
        state_change = True
        state_change_counts += 1
        if (state_change_counts%2) == 0:
            layer_num += 1
    else :
        state_change = False    
    print('Layer '+ str(layer_num)+' Recoating Position',recoater_pos,' State Change ', state_change)
    time.sleep(.25)
  
    if state_change and post_fusion_state: #post fusion layer
        TakeNikonPicture(main_folder+'/optical/Layer'+str(layer_num).zfill(7)+'PF.jpg')
        post_fusion_state = False
    elif state_change and not post_fusion_state: # postrecoating layer
        TakeNikonPicture(main_folder+'/optical/Layer'+str(layer_num-1).zfill(7)+'PR.jpg')
        post_fusion_state = True
        start_stop_infared()
        
        
        
