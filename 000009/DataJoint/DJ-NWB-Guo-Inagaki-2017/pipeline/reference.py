'''
Schema of subject information.
'''
import datajoint as dj

schema = dj.schema(dj.config['custom'].get('database.prefix', '') + 'reference')


@schema
class WholeCellDevice(dj.Lookup):
    definition = """ # Description of the device used for electrical stimulation
    device_name: varchar(32)
    ---
    device_desc = "": varchar(1024)
    """   


@schema
class Probe(dj.Lookup):
    definition = """            # Description of a particular model of probe.
    probe_name: varchar(128)    # String naming probe model
    channel_counts: smallint    # number of channels in the probe
    """

    class Channel(dj.Part):
        definition = """
        -> master
        channel_id: smallint    # id of a channel on the probe
        ---
        channel_x_pos:  float   # x position relative to the tip of the probe (um)
        channel_y_pos:  float   # y position relative to the tip of the probe (um)
        channel_z_pos:  float   # y position relative to the tip of the probe (um)
        shank_id: smallint      # the shank id of this probe this channel is located on 
        """


@schema
class CorticalLayer(dj.Lookup):
    definition = """
    cortical_layer : varchar(8) # layer within cortex
    """
    contents = zip(['N/A', '1', '2', '3', '4', '5', '6', '2/3', '3/4', '4/5', '5/6'])


@schema
class Hemisphere(dj.Lookup):
    definition = """
    hemisphere: varchar(16)
    """
    contents = zip(['left', 'right', 'bilateral'])


@schema
class BrainLocation(dj.Manual): # "dj.Manual" here because, for different session in a dataset, or across different dataset, most likely new applicable brain location will be entered. Unless we have some giant atlas/templates with all brain locations (very unlikely)
    definition = """ 
    brain_region: varchar(32)
    brain_subregion = 'N/A' : varchar(32)
    -> CorticalLayer
    -> Hemisphere
    ---
    brain_location_full_name = 'N/A' : varchar(128)
    """


@schema
class CoordinateReference(dj.Lookup):
    definition = """
    coordinate_ref: varchar(32)
    """
    contents = zip(['lambda', 'bregma'])
    
    
@schema 
class ActionLocation(dj.Manual): 
    definition = """ # Location of any experimental task (e.g. recording (extra/intra cellular), stimulation (photo or current) )
    -> BrainLocation
    -> CoordinateReference
    coordinate_ap: decimal(4,2)    # in mm, anterior positive, posterior negative 
    coordinate_ml: decimal(4,2)    # in mm, always postive, number larger when more lateral
    coordinate_dv: decimal(4,2)    # in mm, always postive, number larger when more ventral (deeper)
    """
 
   
@schema
class AnimalSource(dj.Lookup):
    definition = """
    animal_source: varchar(32)      # source of the animal, Jax, Charles River etc.
    """
    contents = zip(['Jackson', 'Charles River', 'Guoping Feng', 'Homemade'])


@schema
class AnimalSourceAlias(dj.Lookup):
    definition = """
    animal_source_alias: varchar(32)      # other names for source of the animal, Jax, Charles River etc.
    ---
    -> AnimalSource
    """
    contents = [ 
            ['Jackson', 'Jackson'],
            ['Homemade', 'Homemade'],
            ['Jax', 'Jackson'],
            ['JAX', 'Jackson'],
            ['Charles River', 'Charles River'],
            ['Guoping Feng', 'Guoping Feng'],
            ]


@schema
class VirusSource(dj.Lookup):
    definition = """
    virus_source: varchar(64)
    """
    contents = zip(['UNC', 'UPenn', 'MIT', 'Stanford', 'Homemade'])


@schema
class ProbeSource(dj.Lookup):
    definition = """
    probe_source: varchar(64)
    ---
    number_of_channels: int
    """
    contents = [
        ['Cambridge NeuroTech', 64],
        ['NeuroNexus', 32]
    ]


@schema
class Virus(dj.Lookup):
    definition = """
    virus: varchar(64) # name of the virus
    ---
    -> VirusSource
    virus_lot_number="":  varchar(128)  # lot numnber of the virus
    virus_titer=null:       float     # x10^12GC/mL
    """


@schema
class Experimenter(dj.Lookup):
    definition = """
    experimenter: varchar(64)
    """
    contents = [['Nuo Li']]


@schema
class WhiskerConfig(dj.Lookup):
    definition = """
    whisker_config: varchar(32)
    """
    contents = zip(['full', 'C2'])
       
    
@schema
class ExperimentalEvent(dj.Lookup):
    definition = """ # Experimental paradigm events of this study
    event: varchar(32)
    ---
    description: varchar(256)    
    """
    contents = zip(['trial_start', 'trial_stop', 'cue_start', 'cue_end', 'pole_in', 'pole_out'],
                   ['trial start time', 'trial end time',
                    'onset of auditory cue', 'offset of auditory cue',
                    'onset of pole moving in', 'onset of pole moving out'])

    
@schema
class TrialType(dj.Lookup):
    definition = """ # The experimental type of this trial, e.g. Lick Left vs Lick Right
    trial_type: varchar(32)
    """
    contents = zip(['lick left', 'lick right', 'non-performing', 'N/A'])
    
    
@schema
class TrialResponse(dj.Lookup):
    definition = """ # The behavioral response of this subject of this trial - correct/incorrect with respect to the trial type
    trial_response: varchar(32)
    """
    contents = zip(['correct', 'incorrect', 'no response', 'early lick', 'N/A'])
