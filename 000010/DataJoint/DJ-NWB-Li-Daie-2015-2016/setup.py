#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='Li2015',
    version='0.0.0',
    description='Datajoint schemas for Li2015 paper',
    author='Vathes',
    author_email='support@vathes.com',
    license='MIT',
    url='https://github.com/vathes/Li-2015a',
    packages=find_packages(exclude=[]),
    install_requires=requirements,
)
