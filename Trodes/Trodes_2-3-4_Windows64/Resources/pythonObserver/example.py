import random


# Function: Find a new cue0 well completely randomly.
# Input: cue1 and cue2
def set_well_random(cue_1, cue_2):

    list_wells = [0, 1, 2, 3, 4, 5]
    if cue_1 > -1:
        del list_wells[cue_1]  # Remove cue1 from list of wells if it exists
        if cue_2 > -1:
            if cue_1 > cue_2:  # If cue1 is greater, cue2's index is preserved
                del list_wells[cue_2]  # Remove cue2 from list of wells
            elif cue_1 < cue_2:  # If cue2 is greater, cue2's index is shifted over 1
                del list_wells[cue_2 - 1]  # Remove cue2 from list of wells

    # We can edit the following if we want to use a more complex algorithm to calculate
    # the next cue0 (perhaps increase the chance of cue0 being in the same branch as cue1)
    return list_wells[random.randint(0, len(list_wells) - 1)]


# This function MUST BE NAMED 'callback'!!!!
def callback(line):

    # This is the custom callback function. When events occur, addScQtEvent will
    # call this function.
    # newLine is the last text string sent from the microcontroller

    # this function keeps a record of the animal's choices and reward history,
    # and tells the microcontroller which port to arm with reward for the next trial.

    # the history is stored in the global variable scQtHistory for future use,
    # and it is a 2-column matrix [choice reward]

    # custom globals for this task
    global cue0
    global cue1
    global cue2

    if line.find("cue1") >= 0:  # Found cue1 output
        cue1 = int(line[line.find("cue1") + 7])-1  # the -1 is to put cue1 into python 0-index
        print("cue1 updated to: " + str(cue1+1))
    elif line.find("cue2") >= 0:  # Found cue2 output
        cue2 = int(line[line.find("cue2") + 7])-1  # the -1 is to put cue2 into python 0-index
        print("cue2 updated to: " + str(cue2+1))
    elif line.find("PYTHON") >= 0:  # Found triggerword
        print("running set_well_random...")
        cue0 = set_well_random(cue1, cue2)
        print("SCQTMESSAGE: cue0 = " + str(cue0+1) + ";\n")
        print("SCQTMESSAGE: correctwell = cue0;\n")
