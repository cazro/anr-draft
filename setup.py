#!/usr/bin/env python

from setuptools import setup

setup(name='Android Netrunner Discord Draft Bot',
      version='1.0',
      description='A draft bot in Discord for Android Netrunner',
      author='Eric King',
      author_email='edk@ericdavidking.com',
      url='https://github.com/cazro/anr-draft',
      packages=['anrdraft',],
      install_requires=['discord']
     )