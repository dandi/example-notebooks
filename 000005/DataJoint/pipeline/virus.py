'''
Schema of virus
'''
import re
import os
from datetime import datetime

import numpy as np
import scipy.io as sio
import datajoint as dj
import h5py as h5

from . import reference, subject, utilities, stimulation

schema = dj.schema(dj.config['custom']['database.prefix'] + 'virus')


@schema
class VirusSource(dj.Lookup):
    definition = """
    virus_source: varchar(64)
    """
    contents = zip(['UNC', 'UPenn', 'MIT', 'Stanford', 'Homemade'])


@schema
class Virus(dj.Manual):
    definition = """
    virus: varchar(64) # name of the virus
    ---
    -> VirusSource
    virus_lot_number="":  varchar(128)  # lot numnber of the virus
    virus_titer=null:       float     # x10^12GC/mL
    """


@schema
class VirusInjection(dj.Manual):
    definition = """
    -> subject.Subject
    -> reference.BrainLocation
    -> reference.CoordinateReference
    injection_date: date   
    ---
    -> Virus
    injection_volume: float # in nL
    """
