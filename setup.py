import os
from setuptools import (
    setup,
    find_packages
)


with open(os.path.join('requirements.txt'), 'r') as f:
    REQUIRED_PACKAGES = f.readlines()


setup(
    name='peerscount-dags',
    version='0.0.1',
    install_requires=REQUIRED_PACKAGES,
    packages=['peerscout_dags'],
    include_package_data=True,
    description='peerscout dag utils'
)
