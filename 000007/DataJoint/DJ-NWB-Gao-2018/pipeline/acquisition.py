'''
Schema of aquisition information.
'''
import datajoint as dj
from pipeline import reference, subject

schema = dj.schema('gao2018_acquisition')


@schema
class ExperimentType(dj.Lookup):
    definition = """
    experiment_type: varchar(32)
    """
    contents = zip(['behavior', 'extracelluar', 'photostim'])


@schema
class Session(dj.Manual):
    definition = """
    -> subject.Subject
    session_time: datetime    # session time
    ---
    session_directory: varchar(256)
    session_note='': varchar(256) #
    """

    class Experimenter(dj.Part):
        definition = """
        -> master
        -> reference.Experimenter
        """

    class ExperimentType(dj.Part):
        definition = """
        -> master
        -> ExperimentType
        """


@schema
class PhotoStim(dj.Manual):
    definition = """
    -> Session
    ---
    photo_stim_wavelength: int
    photo_stim_method: enum('fiber', 'laser')
    -> reference.BrainLocation
    -> reference.Hemisphere
    -> reference.CoordinateReference
    photo_stim_coordinate_ap: float    # in mm, anterior positive, posterior negative
    photo_stim_coordinate_ml: float    # in mm, always postive, number larger when more lateral
    photo_stim_coordinate_dv: float    # in mm, always postive, number larger when more ventral (deeper)
    """
