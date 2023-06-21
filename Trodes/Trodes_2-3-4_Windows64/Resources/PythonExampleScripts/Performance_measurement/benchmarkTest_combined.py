# import necessary modules
# do `pip install trodesnetwork` to get this package
from trodesnetwork import trodes
from trodesnetwork import socket
import trodesnetwork
import threading
import numpy as np

# os.nice(-19) #for linux only-- increases process priority to max


#dataClient = trodesnetwork.DataClient('tcp://127.0.0.1:49152')
#dataClient.enable('digital')

hardware = trodes.TrodesHardware(server_address="tcp://127.0.0.1:49152")
#mode = 'lfp'
mode = 'spikes'
#mode = 'digital'
#mode = 'waveforms'

input_eventrecord = np.array([])
pulserecord = np.array([])

mcu_byte = 1  # location of the MCU data
#ecu_in_byte = 2  # start location of the ECU digital input data
#ecu_out_byte = 6  # start location of the ECU digital output data

ecu_in_byte = 4  # start location of the ECU digital input data
ecu_out_byte = 8  # start location of the ECU digital output data

# desired_device = ecu_in_byte  # choose the device from the above list
desired_device = ecu_out_byte  # choose the device from the above list
desired_device_channel = 0  # this is 0-based, so '0' is the first channel in the device

numTrials = 101
counter = 0
pulseCounter = 0

lock = 0


def input_event_process_thread():
    global input_eventrecord
    global counter
    global pulseCounter
    global lock
    input_event = socket.SourceSubscriber('source.'+ mode, server_address="tcp://127.0.0.1:49152")
    lastTrialTime = 0
    oldDValue = 0
    newDValue = 0

    while counter < numTrials:

        s = input_event.receive()
        stimestamp = s['localTimestamp']
        log = 0
        if (mode == 'lfp'):
            input_event_data = s['lfpData'][0] #input_event data on the 0th channel
            newDValue = input_event_data
            if (oldDValue >= 0 and newDValue < 0):
                log = 1
        elif (mode == 'spikes' or mode == 'waveforms'):
            #cluster = s['cluster']
            ntrode_id = s['nTrodeId']
            if (ntrode_id == 1):
                log = 1
        elif (mode == 'digital'):
            byte_data = bytearray(s['digitalData'][0])
            channel_data = (byte_data[ecu_out_byte] >> 1) & 1  # Here we isolate just the desired bit
            newDValue = channel_data
            #print(newDValue)		
            if (oldDValue == 0 and newDValue == 1):
                log = 1

        if (log == 1):
            if (counter > 0 and (stimestamp - lastTrialTime) > 60000):
                # we have a misfire
                counter = counter - 1
                input_eventrecord = np.delete(input_eventrecord, -1)

            if (counter == pulseCounter and (stimestamp - lastTrialTime) > 3000 and lock == 0):
                hardware.ecu_shortcut_message(1)
                input_eventrecord = np.append(input_eventrecord, stimestamp)
                print('input_event pulse: ' + str(np.size(input_eventrecord)) + ' ' + str(stimestamp))
                lastTrialTime = stimestamp
                counter = counter + 1

        oldDValue = newDValue


def pulse_process_thread():
    global input_eventrecord
    global pulserecord
    global pulseCounter
    global counter
    global lock
    oldDValue = 0
    newDValue = 0

    dio = socket.SourceSubscriber('source.digital', server_address="tcp://127.0.0.1:49152")
    pulseCounter = 0

    while pulseCounter < numTrials:
        data = dio.receive()

        htimestamp = data['localTimestamp']
        byte_data = bytearray(data['digitalData'][0])
        channel_data = (byte_data[desired_device] >> desired_device_channel) & 1  # Here we isolate just the desired bit
        newDValue = channel_data

        if (oldDValue == 0 and newDValue == 1):
            if (counter == pulseCounter+1):
                lock = 1
                ptimestamp = htimestamp
                pulseCounter = pulseCounter + 1
                pulserecord = np.append(pulserecord, ptimestamp)
                print('Pulse: ' + str(np.size(pulserecord)) + ' ' + str(ptimestamp))
        lock = 0
        oldDValue = newDValue

    diffrecord = np.array([])
    for x in range(numTrials):
        tmpDiff = pulserecord[x] - input_eventrecord[x]
        if (mode == 'spikes' or mode == 'waveforms'):
            tmpDiff = tmpDiff - 0
        if (tmpDiff < 15000):
            diffrecord = np.append(diffrecord, tmpDiff)

    print('MEDIAN: ' + str(np.median(diffrecord)) + ' Min:' + str(np.min(diffrecord)) + ' 90th: ' + str(
        np.percentile(diffrecord, 90)) + ' 99th: ' + str(np.percentile(diffrecord, 99)) + ' Max: ' + str(
        np.max(diffrecord)))


pulse_thread = threading.Thread(target=pulse_process_thread)  # Insert into a thread
print("Pulse thread started")
pulse_thread.start()

# stop_diothread = False
input_event_thread = threading.Thread(target=input_event_process_thread)  # Insert into a thread
print("input_event thread started")
input_event_thread.start()

pulse_thread.join()
input_event_thread.join()


# time.sleep(1)
# stop_diothread = True
# dio_thread.join()
# print("Thread stopped")
