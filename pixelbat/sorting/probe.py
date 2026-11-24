"""Kilosort probe of a Trodes recording from its channel-coordinates file."""
import numpy as np

from pixelbat.utils.readTrodesExtractedDataFile import readTrodesExtractedDataFile

# Shank of each Trodes ML site position (um), Neuropixels 1.0, 2.0 four-shank and UHD layouts
shank_of_ml = {
    -24: 0, -8: 0, 8: 0, 24: 0,
    -383: 0, -351: 0, -133: 1, -101: 1, 117: 2, 149: 2, 367: 3, 399: 3,
    -21: 0, -15: 0, -9: 0, -3: 0, 3: 0, 9: 0, 15: 0, 21: 0,
}


def trodes_probe(coordinates):
    """Kilosort probe dict of every channel of the binary, from its Trodes coordinates file."""
    sites = readTrodesExtractedDataFile(coordinates)['data']
    ml = sites['ml'].ravel()
    return {
        'chanMap': np.arange(len(sites), dtype=np.int32),
        'xc': ml.astype(np.float32),
        'yc': sites['dv'].ravel().astype(np.float32),
        'kcoords': np.array([shank_of_ml[x] for x in ml], dtype=np.float32),
        'n_chan': len(sites),
    }
