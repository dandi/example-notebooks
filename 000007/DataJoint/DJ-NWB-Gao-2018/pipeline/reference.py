'''
Schema of subject information.
'''
import datajoint as dj

schema = dj.schema('gao2018_reference')


@schema
class BrainLocation(dj.Lookup):
    definition = """
    brain_location: varchar(24)
    ---
    brain_location_full_name: varchar(128)
    """
    contents = [
        ['Fastigial', 'Cerebellar fastigial nucleus'],
        ['Dentate', 'Cerebellar dentate nucleus'],
        ['DCN', 'Cerebellar nuclei'],
        ['ALM', 'Anteriror lateral motor cortex']
    ]


@schema
class Hemisphere(dj.Lookup):
    definition = """
    hemisphere: varchar(8)
    """
    contents = zip(['left', 'right'])


@schema
class CoordinateReference(dj.Lookup):
    definition = """
    coordinate_ref: varchar(8)
    """
    contents = zip(['lambda', 'bregma'])


@schema
class ReferenceAtlas(dj.Lookup):
    definition = """
    ref_atlas: varchar(32)
    """
    contents = [['Allen Reference Atlas']]


@schema
class AnimalSource(dj.Lookup):
    definition = """
    animal_source: varchar(16)      # source of the animal, Jax, Charles River etc.
    """
    contents = zip(['JAX', 'Homemade'])


@schema
class VirusSource(dj.Lookup):
    definition = """
    virus_source: varchar(16)
    """
    contents = zip(['UNC', 'UPenn', 'MIT', 'Stanford', 'Homemade'])


@schema
class ProbeSource(dj.Lookup):
    definition = """
    probe_source: varchar(32)
    """


@schema
class Probe(dj.Lookup):
    definition = """ # Description of a particular model of probe.
    probe_type: varchar(64)      # String naming probe model
    ---
    channel_counts: smallint      # number of channels in the probe
    -> ProbeSource
    """

    class Channel(dj.Part):
        definition = """
        -> master
        channel_id:         smallint     # id of a channel on the probe
        ---
        channel_x_pos=null:  float   # x position relative to the tip of the probe (um)
        channel_y_pos=null:  float   # y position relative to the tip of the probe (um)
        channel_z_pos=null:  float   # y position relative to the tip of the probe (um)
        shank_id=null: smallint  # the shank id of this probe this channel is located on
        """


@schema
class Virus(dj.Lookup):
    definition = """
    virus: varchar(32) # name of the virus
    ---
    -> VirusSource
    virus_lot_number="":  varchar(128)  # lot numnber of the virus
    """
    contents = [{
        'virus': 'AAV2-hSyn-hChR2(H134R)-EYFP',
        'virus_source': 'UNC'
    }]


@schema
class Experimenter(dj.Lookup):
    definition = """
    experimenter: varchar(32)
    """
    contents = zip(['Nuo Li'])


@schema
class WhiskerConfig(dj.Lookup):
    definition = """
    whisker_config: varchar(8)
    """
    contents = zip(['full', 'C2'])
