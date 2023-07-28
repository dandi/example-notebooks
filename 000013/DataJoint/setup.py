#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='hires_gutnisky_2015',
    version='0.0.0',
    description='Datajoint schemas for Hires, Gutnisky et al., 2015 from Svoboda Lab',
    author='Vathes',
    author_email='support@vathes.com',
    packages=find_packages(exclude=[]),
    install_requires=requirements
)
