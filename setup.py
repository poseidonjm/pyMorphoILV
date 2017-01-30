#!/usr/bin/env python

"""
setup.py file for pyMorphoILV
"""

from setuptools import setup

setup (name = 'pyMorphoILV',
       use_scm_version=True,
       setup_requires=['setuptools_scm', 'pyusb==1.0.0b1'],
#       version         = '0.1',
       author           = "Alejandro Romero <alromh87@gmail.com>",
       author_email     = "alromh87@gmail.com",
       description      = """Userspace Morpho ILV Driver""",
       py_modules       = ["pyMorphoILV"],
       )

