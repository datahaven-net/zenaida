#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pkgversion import list_requirements, pep440_version, write_setup_py
from setuptools import find_packages

write_setup_py(
    name='zenaida',
    version=pep440_version(),
    description="Open source domain registry system built on top of EPP protocol",
    long_description=open('README.md').read(),
    author="Veselin Penev",
    author_email='penev.veselin@gmail.com',
    url='https://github.com/datahaven-net/zenaida',
    install_requires=list_requirements('requirements/requirements-base.txt'),
    packages=find_packages(),
    tests_require=['tox'],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Environment :: Web Environment',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Topic :: Internet :: WWW/HTTP',
    ]
)
