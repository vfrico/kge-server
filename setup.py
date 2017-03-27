#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 - 2017 Víctor Fernández Rico <vfrico@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup
doc_build_requires = ['sphinx', 'sphinx_rtd_theme',
                      'sphinxcontrib-httpdomain']
execution_requires = ['scikit-kge>=0.9.2', 'annoy', 'nose']
service_requires = ['gunicorn', 'falcon', 'falcon-cors',
                    'celery>=4.0.0', 'redis', 'elasticsearch>=5.0.0,<6.0.0']

# You can tweak this to add or delete dependencies
all_dependencies = doc_build_requires + execution_requires + service_requires

setup(name='kgeserver',
      version='0.1',
      description='Machine learning combined with Knowledge Graph Embeddings',
      author='Víctor Fernández Rico',
      author_email='vfrico@gmail.com',
      url='https://github.com/vfrico/kge-server',
      license='LGPL-v3',

      packages=['kgeserver'],
      dependency_links=[
       'https://github.com/vfrico/scikit-kge/tarball/v0.9.2#egg=scikit-kge-0.9.2'
      ],
      install_requires=all_dependencies,
      keywords=('Knowledge graph, Embeddings, Machine learning,'
                'nearest neighbors, approximate nearest neighbors, ann'
                'rest, service'),
      )

# 'https://github.com/vfrico/scikit-kge/tarball/v0.9#egg=scikit-kge-0.9'
