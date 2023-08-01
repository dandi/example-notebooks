import datajoint as dj


if 'custom' not in dj.config:
    dj.config['custom'] = {}