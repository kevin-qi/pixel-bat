
# example: stimulation pulse train on a single channel
# import necessary modules
# do `pip install trodesnetwork` to get this package
# you will also need to pip install zmq and msgpack

from trodesnetwork import trodes
import time
#hardware = trodes.TrodesHardware(server_address="tcp://127.0.0.1:49152")
hardware = trodes.TrodesHardware()

hardware.sendClearStimulationParams(0) #clear the slot
hardware.sendClearStimulationParams(1) #clear the slot
hardware.sendClearStimulationParams(2) #clear the slot
hardware.sendClearStimulationParams(3) #clear the slot

# set up parameters
globalStimSettings = trodes.GlobalStimulationSettings()
globalStimSettings.setVoltageScale(
    # change this to something reasonable
    #scaleValue = trodes.CurrentScaling.max10nA
    #scaleValue = trodes.CurrentScaling.max20nA
    #scaleValue = trodes.CurrentScaling.max50nA
    #scaleValue = trodes.CurrentScaling.max100nA
    #scaleValue = trodes.CurrentScaling.max200nA
    #scaleValue = trodes.CurrentScaling.max500nA
    #scaleValue = trodes.CurrentScaling.max1uA
    #scaleValue = trodes.CurrentScaling.max2uA
    #scaleValue = trodes.CurrentScaling.max5uA
    scaleValue = trodes.CurrentScaling.max10uA
    )
hardware.sendGlobalStimulationSettings(globalStimSettings)

# all of these values should be changed to something reasonable
stimCommand = trodes.StimulationCommand()
stimCommand.setBiphasicPulseShape(
    leadingPulseWidth_Samples = 50,
    leadingPulseAmplitude = 200,
    secondPulseWidth_Samples = 50,
    secondPulseAmplitude = 200,
    interPhaseDwell_Samples = 5,
    pulsePeriod_Samples = 2000,
    startDelay_Samples = 0
    )
stimCommand.setNumPulsesInTrain(
    numPulsesInTrain = 10
    )
stimCommand.setChannels(
    cathodeID = 2,
    cathodeChannel = 1,
    anodeID = 2,
    anodeChannel = 1
    )
stimCommand.setGroup(
    group=2
    )
stimCommand.setSlot(
    slot=2
    )
hardware.sendStimulationParams(stimCommand)

#



#hardware.sendStimulationStartGroup(0) #run all groups (0)
hardware.sendStimulationStartGroup(2) #run a single group (> 0)
#hardware.sendStimulationStartSlot(0) #Doesn't work










