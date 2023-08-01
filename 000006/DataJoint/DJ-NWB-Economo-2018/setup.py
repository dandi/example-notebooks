#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='Economo2018',
    version='0.0.0',
    description='Datajoint schemas for Economo 2018 paper',
    author='Vathes',
    author_email='support@vathes.com',
    license='MIT',
    url='https://github.com/vathes/Economo-2018',
    packages=find_packages(exclude=[]),
    install_requires=['datajoint'],
)
