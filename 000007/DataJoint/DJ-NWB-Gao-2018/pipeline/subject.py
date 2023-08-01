'''
Schema of subject information.
'''
import datajoint as dj
from pipeline import reference

schema = dj.schema('gao2018_subject')


@schema
class Species(dj.Lookup):
    definition = """
    species: varchar(24)
    """
    contents = zip(['Mus musculus'])


@schema
class Allele(dj.Lookup):
    definition = """
    allele: varchar(24)
    ---
    stock_no: varchar(12)    # Jax strain number
    """


@schema
class Subject(dj.Manual):
    definition = """
    subject: varchar(16)  # name of the subject
    ---
    -> Species
    -> reference.AnimalSource
    sex: enum('M', 'F', 'U')
    date_of_birth: date
    """


@schema
class Zygosity(dj.Manual):
    definition = """
    -> Subject
    -> Allele
    ---
    zygosity:  enum('Homozygous', 'Heterozygous', 'Negative', 'Unknown')
    """
