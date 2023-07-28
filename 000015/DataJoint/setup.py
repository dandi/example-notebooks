#!/usr/bin/env python
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name='li2015b_pipeline',
    version='0.0.0',
    description='Datajoint schemas for Li 2015b',
    author='Vathes',
    author_email='support@vathes.com',
    packages=find_packages(exclude=[]),
    install_requires=['datajoint>=0.12.dev4'],
)
