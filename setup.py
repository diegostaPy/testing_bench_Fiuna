#!/usr/bin/python3

# from Cython.Build import cythonize
from setuptools import setup
# import numpy
import os

# Read the long description from the readme file
with open("README.md", "rb") as f:
    long_description = f.read().decode("utf-8")


# Read the dependencies
thelibFolder = os.path.dirname(os.path.realpath(__file__))
requirementPath = os.path.join(thelibFolder, 'requirements.txt')
install_requires_list = []
if os.path.isfile(requirementPath):
    with open(requirementPath) as f:
        install_requires_list = f.read().splitlines()


# Run setup
setup(name='pytutester',
      packages=['pytutester'],
      package_data={},

      version='1.0',
      description='PytuTester is a open source ventilator tester developed to help bio-engineers in the design specification verification of new ventilators prototypes.  A ventilator tester are to measure the flow,  pressure, volume and oxygen concentration provided to the patient.',
      long_description=long_description,
      url='https://github.com/diegostaPy/testing_bench_Fiuna',
      download_url='diegostaPy/testing_bench_Fiuna/archive/master.zip',
      author='Pytu Colaboration',
      license='MIT',
      include_package_data=False,
      zip_safe=False,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Programming Language :: Python :: 3',
          'Intended Audience :: Science/Research',
      ],
      keywords='Bioengineering',
      install_requires=install_requires_list,
      entry_points={
          'console_scripts': [
              'ARLreader=ARLreader:main',
          ],
      },
      )
