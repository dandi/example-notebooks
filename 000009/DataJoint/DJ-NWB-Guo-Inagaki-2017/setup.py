#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='guo_https:guo_inagaki_2017_pipeline',
    version='0.0.0',
    description='Datajoint schemas for Guo, Inagaki et al., 2018 from Svoboda Lab',
    author='Vathes',
    author_email='support@vathes.com',
    packages=find_packages(exclude=[]),
    install_requires=['datajoint']
)
