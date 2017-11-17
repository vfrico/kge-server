#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
#
# Copyright (C) 2017  Víctor Fernández Rico <vfrico@gmail.com>
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
import sys
sys.path.insert(0, '..')
try:
    # import kgeserver
    import dataset
except ImportError:
    raise


class MusicBrainzDataset(dataset.Dataset):
    def __init__(self, sparql_endpoint=None, thread_limiter=4):
        super(MusicBrainzDataset, self).__init__(
            sparql_endpoint=sparql_endpoint,
            thread_limiter=thread_limiter)

    def load_dataset_from_n3(self, file_readable):
        rt_check = True
        for line in file_readable:
            triple = line.rstrip().split(" ")
            rt_check = rt_check and self.add_triple(triple[0],
                                                    triple[2], triple[1])

        return rt_check


if __name__ == '__main__':
    n3file = open("../ntriples/dbpedia.nt", mode="r")
    n3file2 = open("../ntriples/area.nt", mode="r")
    MBDB = MusicBrainzDataset()
    # MBDB.load_dataset_from_n3(n3file)
    MBDB.load_dataset_from_n3(n3file2)
    MBDB.show()
