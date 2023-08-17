from setuptools import setup

setup(
     # Needed to silence warnings (and to be a worthwhile package)
    name='Measurements',
    url='https://github.com/JonasBVG/TripPy.git',
    author='Jonas Huebner',
    author_email='jonas.huebner@bvg.de',
    # Needed to actually package something
    packages=['trippy'],
    # Needed for dependencies
    install_requires=['geopandas'],
    # *strongly* suggested for sharing
    version='0.1',
    # The license can be anything you like
    license='GPL-3.0',
    description='Module to analyze trip tables and to create reports from MATSim runs',
    
    # long_description=open('README.txt').read(),
)
