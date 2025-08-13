dataPath = 'C:\Users\batlab\Desktop\14445\20231206_185540_probe1.rec\20231206_185540_probe1.LFP';
chs = [1301:2:1357];
for ch = chs
    lfp = readTrodesExtractedDataFile(fullfile(dataPath, sprintf('20231206_185540_probe1.LFP_nt%dch1.dat',ch)));
    disp(prctile(abs(lfp.fields.data),99.99))
    histogram(lfp.fields.data, [-32777:1000:32777])
    hold on   
end

dataPath = 'C:\Users\batlab\Desktop\14445\20231206_185540_probe1.rec\20231206_185540_probe1.spikeband';
chs = [1301:2:1357];
for ch = chs
    lfp = readTrodesExtractedDataFile(fullfile(dataPath, sprintf('20231206_185540_probe1.spikeband_nt%dch1.dat',ch)));
    disp(prctile(abs(lfp.fields.data),99.99))
end