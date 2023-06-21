# import necessary modules
# do `pip install trodesnetwork` to get this package
from trodesnetwork import trodes
from trodesnetwork import socket
import threading
import math



# os.nice(-19) #for linux only-- increases process priority to max


hardware = trodes.TrodesHardware(server_address="tcp://127.0.0.1:49152")
mode = 'lfp'
#mode = 'spikes'
#mode = 'digital'
#mode = 'waveforms'



mcu_byte = 1  # location of the MCU data
ecu_in_byte = 2  # start location of the ECU digital input data
ecu_out_byte = 6  # start location of the ECU digital output data

# desired_device = ecu_in_byte  # choose the device from the above list
desired_device = ecu_out_byte  # choose the device from the above list
desired_device_channel = 0  # this is 0-based, so '0' is the first channel in the device

numTrials = 1000
counter = 0
pulseCounter = 0

lock = 0


def input_event_process_thread():
    
    global counter
    global pulseCounter
    global lock
    input_event = socket.SourceSubscriber('source.'+ mode, server_address="tcp://127.0.0.1:49152")
    lastTrialTime = 0
    newTime = 0
    oldTime = 0
    
    newDValue = 0

    while counter < numTrials:

        s = input_event.receive()
        stimestamp = s['localTimestamp']
        log = 0
        if (mode == 'lfp'):
            input_event_data = s['lfpData'][0] #input_event data on the 0th channel
            newDValue = input_event_data
            
        elif (mode == 'spikes' or mode == 'waveforms'):
            #cluster = s['cluster']
            ntrode_id = s['nTrodeId']
            newDValue = ntrode_id
            
        elif (mode == 'digital'):
            byte_data = bytearray(s['digitalData'][0])
            channel_data = (byte_data[ecu_out_byte] >> 1) & 1  # Here we isolate just the desired bit
            newDValue = channel_data
            

        #print(newDValue)
        newTime = math.floor((stimestamp/30000)%60)
        if (newTime != oldTime):
            print(newTime)
        oldTime = newTime



input_event_thread = threading.Thread(target=input_event_process_thread)  # Insert into a thread
print("input_event thread started")
input_event_thread.start()

input_event_thread.join()


# time.sleep(1)
# stop_diothread = True
# dio_thread.join()
# print("Thread stopped")
