import readTrodesExtractedDataFile3 as trodesReader
data = trodesReader.readTrodesExtractedDataFile('/home/spikegadgets/datadump/dioexport/dioexport.DIO/dioexport.dio_ECU_Dout1.dat')
print(data['data'])