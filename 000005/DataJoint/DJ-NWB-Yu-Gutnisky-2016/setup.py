#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='yg2016_pipeline',
    version='0.0.0',
    description='Datajoint schemas for Yu and Gutnisky et al., 2016 from Svoboda Lab',
    author='Vathes',
    author_email='support@vathes.com',
    packages=find_packages(exclude=[]),
    install_requires=['datajoint']
)
