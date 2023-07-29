from pipeline.export import datajoint_to_nwb
from pipeline import acquisition


for session in acquisition.Session.fetch('KEY'):
    datajoint_to_nwb.export_to_nwb(session, save=True)
