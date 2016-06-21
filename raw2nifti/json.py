import json
import os
import os.path as op

def create_json_metadata(ftype):

    pass

json_fields = {}
json_fields['bold'] = ['RepetitionTime', 'TaskName', 'SliceTiming']
json_fields['T1w'] = ''
json_fields['T2w'] = ''
json_fields['dwi'] = ['PhaseEncodingDirection', 'EffectiveEchoSpacing', 'EchoTime']
json_fields['topup'] = ['IntendedFor', 'PhaseEncodingDirection']
json_fields['b0'] = ''
json_fields['physio'] = ['sampling_rate']
