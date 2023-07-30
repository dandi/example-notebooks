'''
Schema of virus
'''
import datajoint as dj
from . import get_schema_name
from . import lab, experiment

schema = dj.schema(get_schema_name('virus'))


@schema
class Virus(dj.Manual):
    definition = """
    virus: varchar(64) # name of the virus
    ---
    -> lab.VirusSource
    virus_lot_number="":  varchar(128)  # lot numnber of the virus
    virus_titer=null:       float     # x10^12GC/mL
    """


@schema
class VirusInjection(dj.Manual):
    definition = """
    -> lab.Subject
    injection_id: int   
    ---
    -> Virus
    injection_date: date   
    injection_volume: float # in nL
    -> lab.BrainArea
    -> lab.Hemisphere
    """

    class InjectionLocation(dj.Part):
        definition = """
        -> master
        ---
        -> lab.SkullReference
        ap_location: decimal(6, 2) # (um) from ref; anterior is positive; based on manipulator coordinates/reconstructed track
        ml_location: decimal(6, 2) # (um) from ref ; right is positive; based on manipulator coordinates/reconstructed track
        dv_location: decimal(6, 2) # (um) from dura to first site of the probe; ventral is negative; based on manipulator coordinates/reconstructed track
        theta=null:       decimal(5, 2) # (degree)  rotation about the ml-axis 
        phi=null:         decimal(5, 2) # (degree)  rotation about the dv-axis
        beta=null:        decimal(5, 2) # (degree)  rotation about the shank of the probe
        """
