""" 
filename: PythonObserver.py
Mattias Karlsson, edited by Kevin Fan
Written: 01/06/2016
Updated last: 01/14/2016

Directions: 
In statescript -> Edit -> Local callback language, select Python and specify Python directory.
PythonObserver.py and your callback python script must be in the same directory.
Select that directory in statescript -> File -> Script folders -> Local callback scripts.
After loading your statescript code into the ECU, select your desired callback script and click the Python button.
Click the Python Tab to view your running callback script.

*Note: Your callback script MUST contain a function "def callback(line):" which is called every time statescript outputs a line.

"""

# -=-=-=-=-=-=-=-=-=-=-=-=- startScQt FUNCTION -=-=-=-=-=-=-=-=-=-=-=-=-
def startScQt(callBackFcn, initFcn=""):
    # This function starts the scQt agent in python
    # callBackFcn -- a string containing the name of the callback function to
    #                be called for every new event.
    # initFcn -- <optional> a string containing the name of a function to call
    #            now. Useful for setting up extra global variables or plots.

    global scQtHistory  # multipurpose place to store processed event history
    global scQtControllerOutput  # the text output from the microcontroller
    global scQtCallBackHandle  # the handle to the function called for every new event
    global scQtInitiated  # the callback function should set this to 1 once all user variables are set
    scQtCallBackHandle = __import__(callBackFcn).callback
    scQtControllerOutput = []
    scQtHistory = []
    scQtInitiated = 0

    # Run init function if given
    if initFcn:
        eval(initFcn)

    print("Initiation complete. Running " + callBackFcn + "...")


# -=-=-=-=-=-=-=-=-=-=-=-=- addScQtEvent FUNCTION -=-=-=-=-=-=-=-=-=-=-=-=-
def addScQtEvent(eventString):
    # This function is called by the qt-based gui every time a new even occurs.
    # The event string is passed in the input, and the designated callBack
    # function is called.

    global scQtHistory  # multipurpose place to store processed event history
    global scQtControllerOutput  # the text output from the microcontroller
    global scQtCallBackHandle  # the handle to the function called for every new event

    # add the event output string to the memory log
    scQtControllerOutput.append(eventString)

    # call the callback
    scQtCallBackHandle(eventString)


# -=-=-=-=-=-=-=-=-=-=-=-=- INITIATION FUNCTIONS -=-=-=-=-=-=-=-=-=-=-=-=-
def init():
    print("init function has been run")

