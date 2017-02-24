import os.path as op
from bidsconverter.setup_BIDS import BIDSConstructor

directory = '/media/lukas/piop/Spynoza/test_data/data_piop'
config = op.join(directory, 'config.json')

bids_constructor = BIDSConstructor(directory, config)
bids_constructor.convert2bids()