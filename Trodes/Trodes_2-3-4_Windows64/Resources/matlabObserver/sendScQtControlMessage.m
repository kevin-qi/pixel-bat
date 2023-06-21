function sendScQtControlMessage(message)
%sendScQtControlMessage(message)
%Used to send a string message back to the qt gui.  The
%message is passed directly to the stateScript controller.

disp(['SCQTMESSAGE: ',message,';']);