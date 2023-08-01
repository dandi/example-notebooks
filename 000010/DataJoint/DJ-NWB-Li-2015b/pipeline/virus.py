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
    injection_id: int       # injection number
    ---
    -> Virus
    injection_date: date    # date of injection
    injection_volume: float # volume of virus, in nL
    virus_dilution=null: float   # 1:X dilution
    -> experiment.BrainLocation
    ml_location=null: float # um from ref ; right is positive; based on manipulator coordinates/reconstructed track
    ap_location=null: float # um from ref; anterior is positive; based on manipulator coordinates/reconstructed track
    dv_location=null: float # um from dura; ventral is positive; based on manipulator coordinates/reconstructed track
    """
