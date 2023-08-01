'''
Schema of session information.
'''
import datajoint as dj
from pipeline import reference, subject

schema = dj.schema('gao2018_action')


@schema
class Weighing(dj.Manual):
    definition = """
    -> subject.Subject
    ---
    weight_before: float   # in grams
    weight_after: float    # in grams
    """


@schema
class SubjectWhiskerConfig(dj.Manual):
    definition = """
    -> subject.Subject
    ---
    -> reference.WhiskerConfig
    """


@schema
class VirusInjection(dj.Manual):
    definition = """
    -> subject.Subject
    -> reference.Virus
    -> reference.BrainLocation
    -> reference.Hemisphere
    injection_date: date
    ---
    injection_volume: float # in nL
    injection_coordinate_ap: float   # in mm, negative if posterior, positive if anterior
    injection_coordinate_ml: float   # in mm, always positive, larger number if more lateral
    injection_coordinate_dv: float   # in mm, always positive, larger number if more ventral (deeper)
    -> reference.CoordinateReference
    """
