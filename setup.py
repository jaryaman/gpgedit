#!/usr/bin/env python3

import sys
from setuptools import find_packages
from setuptools import setup

def readToList(fileName):
    return [line.strip() for line in open(fileName).readlines()] 

if '__main__' == __name__:
    requirements = readToList('requirements.txt')
    setup(
        author='Juvid Aryaman',
        author_email='j.aryaman25@gmail.com',
        install_requires = requirements,
        packages=find_packages(),
        license=open('LICENSE.txt').read(),
        long_description=open('README.md').read(),
        name='gpgedit',
        version=open('version.txt').read().strip(),
    )

sys.exit(0)
