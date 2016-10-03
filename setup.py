#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 Víctor Fernández Rico <vfrico@gmail.com>
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

setup(name='kgeserver',
      version='0.1',
      description='Machine learning combined with Knowledge Graph Embeddings',
      author='Víctor Fernández Rico',
      author_email='vfrico@gmail.com',
      url='https://github.com/vfrico/kge-server',
      license='LGPL-v3',

      packages=['kgeserver'],
      dependency_links=[
       'https://github.com/vfrico/scikit-kge/tarball/v0.9#egg=scikit-kge-0.9'
      ],
      install_requires=['scikit-kge', 'annoy'],
      keywords=('Knowledge graph, Embeddings, Machine learning,'
                'nearest neighbors, approximate nearest neighbors, ann'),

      )
