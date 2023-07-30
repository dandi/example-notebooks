#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='gao_2018_pipeline',
    version='0.0.0',
    description='Datajoint schemas for Gao et al., 2018 from Li Lab',
    author='Vathes',
    author_email='support@vathes.com',
    packages=find_packages(exclude=[]),
    install_requires=['datajoint'],
    scripts=['scripts/gao2018-shell.py'],
)
