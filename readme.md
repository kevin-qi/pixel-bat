# PixelBat

## Installation

## Usage
#### Trodes Data Extraction

1. Run `extractAllTrodesRecording(data_path, useMerged, trodes_path)`
	- `data_path`: Path to directory containing .rec folders
	- `isTethered`: false to use merged .rec file (untethered recordings), true to use normal .rec file (tethered recordings)
	- `trodes_path`: Path to directory containing Trodes installation. 
2. Run `kilosort` in matlab console
	- Select `*.kilosort/*.dat` file in your recording directory as data file
	- Select `*.kilosort/kilosort_workdir` as working directory
	- Select `*.kilosort/kilosort_workdir` as out directory
	- Select `*.kilosort/channelMap_*.mat` as channel map (click `other` in channel map dropdown menu)
	- Check that matlab console shows no errors.
	- Click `Run All`
3. Kilosort diagnostics
	- Drift should be <20 um at most. 
5. 