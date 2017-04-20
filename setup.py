import bidsconverter
from setuptools import setup, find_packages

REQUIREMENTS = [
    'scipy>=0.17',
    'numpy>=1.10',
    'scikit-learn>=0.17',
    'pandas>=0.17',
    'nibabel>=2.0',
    'joblib'
]

VERSION = bidsconverter.__version__

def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name='BidsConverter',
    version=VERSION,
    description='Tool to convert raw data sets to BIDS-compatible data sets.',
    long_description=readme(),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Science/Research',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics'],
    keywords="BIDS fMRI MRI reproducibility OpenfMRI",
    url='https://github.com/lukassnoek/BidsConverter',
    author='Lukas Snoek',
    author_email='lukassnoek@gmail.com',
    license='MIT',
    platforms=['Linux', 'Mac OSX'],
    packages=find_packages(),
    install_requires=REQUIREMENTS,
    scripts=['bin/convert2bids', 'bin/fetch_testdata'],
    include_package_data=True,
    zip_safe=False)
