from setuptools import setup, find_packages
import spynoza

VERSION = spynoza.__version__

def readme():
    with open('README.md') as f:
        return f.read()

install_requires = [
    'nibabel',
    'nipype',
    'numpy',
    'scipy'
]

setup(
    name='spynoza',
    version=VERSION,
    description='Python package for fMRI data processing',
    long_description=readme(),
    requires=install_requires,
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 2.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics'],
    keywords="fMRI nipype preprocessing",
    url='https://github.com/spinoza-centre',
    author='Spinoza centre',
    license='MIT',
    platforms='Linux',
    packages=find_packages(),
    zip_safe=False)
