# Copyright 2018 Spanish National Research Council (CSIC)
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from setuptools import setup

setup(
    name='bulksend2cmdb',
    version='1.0.0',
    description='Script for storing CIP data on CMDBv1',
    url='https://github.com/orviz/bulksend2cmdb',
    author='Pablo Orviz',
    author_email='orviz@ifca.unican.es',
    license='Apache 2.0',
    packages=['bulksend2cmdb'],
    package_dir={'bulksend2cmdb': 'bulksend2cmdb'},
    install_requires=[
        'requests',
        'simplejson',
        'six',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': ['bulksend2cmdb=bulksend2cmdb.main:main']
    }
)
