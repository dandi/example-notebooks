import datajoint as dj
from . import get_schema_name

schema = dj.schema(get_schema_name('lab'))


@schema
class Person(dj.Manual):
    definition = """
    username : varchar(24) 
    ----
    fullname : varchar(255)
    """


@schema
class Rig(dj.Manual):
    definition = """
    rig             : varchar(24)
    ---
    room            : varchar(20) # example 2w.342
    rig_description : varchar(1024) 
    """

@schema
class Species(dj.Lookup):
    definition = """
    species: varchar(24)
    """
    contents = zip(['Mus musculus'])


@schema
class AnimalStrain(dj.Lookup):
    definition = """
    animal_strain       : varchar(30)
    """
    contents = zip(['pl56', 'kj18'])


@schema
class AnimalSource(dj.Lookup):
    definition = """
    animal_source       : varchar(30)
    """
    contents = zip(['Jackson Labs', 'Allen Institute', 'Charles River', 'MMRRC', 'Taconic', 'Other'])


@schema
class ModifiedGene(dj.Manual):
    definition = """
    gene_modification   : varchar(60)
    ---
    gene_modification_description = ''         : varchar(256)
    """


@schema
class Subject(dj.Manual):
    definition = """
    subject_id          : int   # institution 6 digit animal ID
    ---
    -> [nullable] Person        # person responsible for the animal
    cage_number=null    : int   # institution 6 digit animal ID
    date_of_birth=null  : date  # format: yyyy-mm-dd
    sex                 : enum('M','F','Unknown')
    -> Species
    -> [nullable] AnimalSource  # where was the animal ordered from
    """

    class Strain(dj.Part):
        definition = """
        # Subject strains
        -> master
        -> AnimalStrain
        """

    class GeneModification(dj.Part):
        definition = """
        # Subject gene modifications
        -> master
        -> ModifiedGene
        ---
        zygosity = 'Unknown' : enum('Het', 'Hom', 'Unknown')
        type = 'Unknown'     : enum('Knock-in', 'Transgene', 'Unknown')
        """


@schema
class CompleteGenotype(dj.Computed):
    # should be computed
    definition = """
    -> Subject
    ---
    complete_genotype : varchar(1000)
    """

    def make(self, key):
        pass


@schema
class WaterRestriction(dj.Manual):
    definition = """
    -> Subject
    ---
    water_restriction_number    : varchar(16)   # WR number
    cage_number                 : int
    wr_start_date               : date
    wr_start_weight             : Decimal(6,3)
    """


@schema
class VirusSource(dj.Lookup):
    definition = """
    virus_source   : varchar(60)
    """
    contents = zip(['Janelia core', 'UPenn', 'Addgene', 'UNC', 'Other'])


@schema
class SkullReference(dj.Lookup):
    definition = """
    skull_reference   : varchar(60)
    """
    contents = zip(['Bregma', 'Lambda'])

    
@schema
class BrainArea(dj.Lookup):
    definition = """
    brain_area: varchar(32)
    ---
    description = null : varchar (4000) # name of the brain area
    """
    contents = [('ALM', 'anterior lateral motor cortex'),
                ('M2', 'secondary motor cortex'),
                ('PONS', 'pontine nucleus'),
                ('vS1', 'vibrissal primary somatosensory cortex ("barrel cortex")'),
                ('Thalamus', 'Thalamus'),
                ('Medulla', 'Medulla'),
                ('Striatum', 'Striatum')]
    
    
@schema
class Hemisphere(dj.Lookup):
    definition = """
    hemisphere: varchar(32)
    """
    contents = zip(['left', 'right', 'both'])


@schema
class ProbeType(dj.Lookup):
    definition = """
    probe_type: varchar(32)    
    """

    contents = zip(['nn_silicon_probe', 'tetrode_array', 'neuropixel'])


@schema
class Probe(dj.Lookup):
    definition = """  # represent a physical probe
    probe: varchar(32)  # unique identifier for this model of probe (e.g. part number)
    ---
    -> ProbeType
    probe_comment='' :  varchar(1000)
    """

    class Electrode(dj.Part):
        definition = """
        -> master
        electrode: int     # electrode
        ---
        x_coord=NULL: float   # (um) x coordinate of the electrode within the probe
        y_coord=NULL: float   # (um) y coordinate of the electrode within the probe
        z_coord=NULL: float   # (um) z coordinate of the electrode within the probe
        """


@schema
class ElectrodeConfig(dj.Lookup):
    definition = """
    -> Probe
    electrode_config_name: varchar(16)  # user friendly name
    ---
    electrode_config_hash: varchar(36)  # hash of the group and group_member (ensure uniqueness)
    unique index (electrode_config_hash)
    """

    class ElectrodeGroup(dj.Part):
        definition = """
        # grouping of electrodes to be clustered together (e.g. a neuropixel electrode config - 384/960)
        -> master
        electrode_group: int  # electrode group
        """

    class Electrode(dj.Part):
        definition = """
        -> master.ElectrodeGroup
        -> Probe.Electrode
        """


@schema
class PhotostimDevice(dj.Lookup):
    definition = """
    photostim_device  : varchar(20)
    ---
    excitation_wavelength :  decimal(5,1)  # (nm) 
    photostim_device_description : varchar(255)
    """
    contents = [('LaserGem473', 473, 'Laser (Laser Quantum, Gem 473)'),
                ('LaserCoboltMambo100', 594, 'Laser (Laser Quantum, Gem 473)'),
                ('LED470', 470, 'LED (Thor Labs, M470F3 - 470 nm, 17.2 mW (Min) Fiber-Coupled LED)'),
                ('OBIS470', 473, 'OBIS 473nm LX 50mW Laser System: Fiber Pigtail (Coherent Inc)')]
