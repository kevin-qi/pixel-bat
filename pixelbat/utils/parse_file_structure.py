import os
import glob
import re

def parse_file_structure(dataset_path: str, bat_id: str, experiment: str, date: str, verbose: bool = True) -> dict:
    """
    Parse recording folder structure and return paths dictionary.
    
    Args:
        dataset_path: Root path to the dataset
        bat_id: ID of the bat (e.g., '14556')
        experiment: Type of experiment (e.g., 'tethered')
        date: Date of recording (e.g., '241225')
    
    Returns:
        Dictionary containing all relevant paths
    """

    # Construct base paths
    raw_path = os.path.join(dataset_path, bat_id, experiment, 'raw', date)
    ephys_path = os.path.join(raw_path, 'ephys')
    
    # Find .rec folder
    rec_folders = glob.glob(os.path.join(ephys_path, '*.rec'))
    if len(rec_folders) != 1:
        raise ValueError(f"Expected exactly 1 .rec folder, found {len(rec_folders)}")
    path_to_rec_dir = rec_folders[0]
    
    # Find .kilosort folder and parse timestamp
    extracted_binaries_dir = glob.glob(os.path.join(path_to_rec_dir, '*.kilosort'))
    if verbose:
        print(f'Parsing file structure for {bat_id} on {date} for {experiment} experiment')
        print(f'Found {len(extracted_binaries_dir)} .kilosort folders')
    
    if(len(extracted_binaries_dir) != 1):
        raise ValueError(f"Expected exactly 1 .kilosort folder, found {len(extracted_binaries_dir)}")
    extracted_binaries_dir = extracted_binaries_dir[0]

    fname = os.path.basename(extracted_binaries_dir)
    yyyy, mm, dd, hhmmss, merged_flag = re.findall(r'(\d\d\d\d)(\d\d)(\d\d)_(\d\d\d\d\d\d)(.*).kilosort', fname)[0]
    
    # Count probes and construct paths
    num_probes = len(glob.glob(os.path.join(extracted_binaries_dir, '*.probe*.dat')))
    if verbose:
        print(f'Found {num_probes} probes')

    paths = {
        'raw_path': raw_path,
        'ephys_path': ephys_path,
        'rec_folder': path_to_rec_dir,
        'kilosort_folder': extracted_binaries_dir,
        'rec_path': os.path.join(path_to_rec_dir, f'{yyyy}{mm}{dd}_{hhmmss}_merged.rec'),
        'timestamp_path': os.path.join(extracted_binaries_dir, f'{yyyy}{mm}{dd}_{hhmmss}{merged_flag}.timestamps.dat'),
        'channelmap_json_paths': [os.path.join(extracted_binaries_dir, f'{bat_id}_{date}_{experiment}_channelmap_probe{iProbe+1}.json') for iProbe in range(num_probes)],
        'kilosort_out_paths': [os.path.join(path_to_rec_dir, f'kilosort_outdir_probe{iProbe+1}') for iProbe in range(num_probes)],
        'num_probes': num_probes,
        'binary_paths': [],
        'channelmap_paths': [],
        'kilosort_binary_paths': []
    }
    
    for iProbe in range(num_probes):
        paths['binary_paths'].append(
            os.path.join(extracted_binaries_dir, f'{yyyy}{mm}{dd}_{hhmmss}{merged_flag}.probe{iProbe+1}.dat'))
        paths['channelmap_paths'].append(
            os.path.join(extracted_binaries_dir, f'{yyyy}{mm}{dd}_{hhmmss}{merged_flag}.channelmap_probe{iProbe+1}.dat'))
        paths['kilosort_binary_paths'].append(
            os.path.join(extracted_binaries_dir, f'{yyyy}{mm}{dd}_{hhmmss}_merged.probe{iProbe+1}.dat'))
    
    return paths