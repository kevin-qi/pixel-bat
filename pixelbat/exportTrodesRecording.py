import os
import re
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import subprocess
import argparse
from utils.readTrodesExtractedDataFile3 import readTrodesExtractedDataFile

def export_trodes_recording(
    path_to_rec_dir: str,
    path_to_trodes: str,
    is_tethered: bool = False,
    extract_lfp: bool = True,
    extract_analog: bool = True,
    extract_kilosort: bool = True,
    extract_time: bool = True,
    extract_dio: bool = True,
    extract_spikes: bool = True,
    extract_spike_band: bool = True,
    extract_raw: bool = False,
    lfp_low_pass: int = 500,
    spikes_freq_band: Tuple[int, int] = (600, 6000)
) -> None:
    """
    Export recording data streams from a Trodes .rec file.

    Args:
    path_to_rec_dir: Path to recording directory
    path_to_trodes: Path to Trodes installation
    is_tethered: Whether recording is tethered (False for wireless)
    extract_lfp: Extract LFP data
    extract_analog: Extract analog data
    extract_kilosort: Extract Kilosort data
    extract_time: Extract timing data
    extract_dio: Extract DIO data
    extract_spikes: Extract spike data
    extract_spike_band: Extract spike band data
    extract_raw: Extract raw data
    lfp_low_pass: LFP low pass filter frequency
    spikes_freq_band: Spike frequency band (low, high)
    """
    print(f"Extracting data from {path_to_rec_dir}\n")

    # Select appropriate flags for extraction
    possible_flags = ["-lfp", "-analogio", "-kilosort", "-dio", "-spikes", "-spikeband", "-time", "-raw"]
    flags = [flag for flag, extract in zip(possible_flags,
    [extract_lfp, extract_analog, extract_kilosort, extract_dio,
     extract_spikes, extract_spike_band, extract_time, extract_raw]) if extract]

    # Build command flags
    cmd_flags = " ".join(flags)

    # LFP and spike band options
    lfp_options = f"-lfplowpass {lfp_low_pass} -lfpoutputrate 1500 -uselfpfilters 0"
    spikeband_options = f"-spikehighpass {spikes_freq_band[0]} -spikelowpass {spikes_freq_band[1]} -usespikefilters 0"

    cmd_flags = f"{cmd_flags} {lfp_options} {spikeband_options}"

    # Get path to trodesexport executable
    if os.name == 'nt':  # Windows
        trodesexport_path = os.path.join(path_to_trodes, 'trodesexport.exe')
    else:  # Unix-like systems
        trodesexport_path = os.path.join(path_to_trodes, 'trodesexport')

    if not os.path.exists(trodesexport_path):
        raise FileNotFoundError(f"trodesexport executable not found at {trodesexport_path}")

    # Parse recording directory
    dirpath, dirname = os.path.split(path_to_rec_dir)
    pattern = r"(\d{4})(\d{2})(\d{2})_(\d{6})\.rec"
    match = re.search(pattern, dirname)

    if match:
        yy, mm, dd, time = match.groups()
        yy = yy[2:]  # Get last two digits of year
        date = f"{yy}{mm}{dd}"

        # Build path to rec file
        suffix = "_merged.rec" if not is_tethered else ".rec"
        rec_filename = dirname.replace(".rec", suffix)
        path_to_rec_file = os.path.join(path_to_rec_dir, rec_filename)

        if os.path.exists(path_to_rec_file):
            # Prepare command
            formatted_path_to_rec_file = f'"{path_to_rec_file}"'
            output_path = f'"{path_to_rec_dir}"'

            cmd = [
                trodesexport_path,
                *cmd_flags.split(),
                '-rec', path_to_rec_file,
                '-outputdirectory', path_to_rec_dir,
                '-interp', '0'
            ]

            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            print(result.stdout)


    else:
        print("Recording file does not exist")

def parse_args():
    parser = argparse.ArgumentParser(description='Export recording data streams from a Trodes .rec file')

    # Required arguments
    parser.add_argument('path_to_rec_dir', type=str,
      help='Path to recording directory')
    parser.add_argument('path_to_trodes', type=str,
      help='Path to Trodes installation')

    # Optional arguments
    parser.add_argument('--is_tethered', action='store_true',
      help='Whether recording is tethered (default: False)')
    parser.add_argument('--no-lfp', action='store_false', dest='extract_lfp',
      help='Skip LFP data extraction')
    parser.add_argument('--no-analog', action='store_false', dest='extract_analog',
      help='Skip analog data extraction')
    parser.add_argument('--no-kilosort', action='store_false', dest='extract_kilosort',
      help='Skip Kilosort data extraction')
    parser.add_argument('--no-time', action='store_false', dest='extract_time',
      help='Skip time data extraction')
    parser.add_argument('--no-dio', action='store_false', dest='extract_dio',
      help='Skip DIO data extraction')
    parser.add_argument('--no-spikes', action='store_false', dest='extract_spikes',
      help='Skip spike data extraction')
    parser.add_argument('--no-spikeband', action='store_false', dest='extract_spike_band',
      help='Skip spike band data extraction')
    parser.add_argument('--extract-raw', action='store_true', dest='extract_raw',
      help='Extract raw data (default: False)')
    parser.add_argument('--lfp-low-pass', type=int, default=500,
      help='LFP low pass filter frequency (default: 500)')
    parser.add_argument('--spikes-freq-band', type=int, nargs=2, default=[600, 6000],
      help='Spike frequency band as two integers: low high (default: 600 6000)')

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    # Convert args namespace to dictionary and pass as kwargs
    kwargs = vars(args)
    spikes_freq_band = kwargs.pop('spikes_freq_band')  # Remove and handle separately
    kwargs['spikes_freq_band'] = tuple(spikes_freq_band)  # Convert list to tuple

    export_trodes_recording(**kwargs)
