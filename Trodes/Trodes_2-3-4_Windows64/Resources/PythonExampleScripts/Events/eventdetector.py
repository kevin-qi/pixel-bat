
# example: detect a specific event
# import necessary modules
# do `pip install trodesnetwork` to get this package
# you will also need to pip install zmq and msgpack

from trodesnetwork import trodes
from trodesnetwork import events
from trodesnetwork import socket
from trodesnetwork.socket import SinkSubscriber, SourcePublisher, SinkPublisher, SourceSubscriber
import time
#hardware = trodes.TrodesHardware(server_address="tcp://127.0.0.1:49152")
hardware = trodes.TrodesHardware()

def receive_zone_event():
    print('Received zone event.')


#events_subscriber = events.EventSubscriber(
#server_address="tcp://127.0.0.1:49152",
#event_name="Zone 0 entered",
#callback=receive_zone_event)

ev_sub = SourceSubscriber(
'trodes.event',
server_address="tcp://127.0.0.1:49152")


while True:
    res = ev_sub.receive()
    print(res['name'], "at time", res['localTimestamp'])
    
    
        
    
