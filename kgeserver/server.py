#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# Dataset class: create, modify, export and import Datasets from Wikidata
# Copyright (C) 2016  Víctor Fernández Rico <vfrico@gmail.com>
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
import os
import kgeserver.dataset as dataset
import kgeserver.algorithm as algorithm
import skge
from annoy import AnnoyIndex


class Server():
    def __init__(self, search_index):
        """Creates a server, given a indexed search tree

        :param SearchIndex search_index: A ready search index
        """
        if not search_index or search_index.index is None:
            print("The search index has not been generated")
            return None
        elif not search_index.ready:
            print("The search index must be built")
            return None
        else:
            self.index = search_index.index

    def similarity_by_id(self, id, k):
        """Given an entity id, return the k'th most similar entities

        Returns a list of pairs, where the first item is the entity
        and the second item is the distance to entity.

        :param int id: The entity id
        :param int k: The entities to show
        :returns: A list with k id's, which are the most similar entities
        :rtype: list of pairs
        """
        sim = self.index.get_nns_by_item(id, k, include_distances=True)
        return [(sim[0][i], sim[1][i]) for i in range(0, len(sim[0]))]

    def similarity_by_vector(vector, k):
        """For each id in vector, return a list with k similar entities

        :param list vector: A list with entity id's
        :param int k: The similar entities shown for each entity
        :returns: a matrix array [][]
        :rtype: list
        """
        matrix = []
        for entity in vector:
            matrix.append(self.similarity_by_id(entity, k))

        return matrix

    def similarity_by_embedding(embedding, k):
        """For a given embedding, return most similar id's

        :param list embedding: An embedding vector
        :param int k: The similar entities shown for each entity
        :returns: A list with k id's, which are the most similar entities
        :rtype: list
        """
        return self.index.get_nns_by_vector(embedding, k)


class SearchIndex():
    def __init__(self):
        """Generates a new SearchIndex, used in Server Class

        The main purpose of this class is to generate an index, without
        the Server class needs to know the search index it is being used

        A search index is ready to be used when an index exists
        and it isready (when an index has been built).
        """
        self.index = None
        self.ready = False

    def build_from_trained_model(self, trained_model, depth):
        """Creates an index from a trained model

        :param TrainedModel trained_model: The trained model
        :param int depth: The depth desired to generate the search index
        """
        entities_matrix = trained_model.E
        nrows, emb_size = entities_matrix.shape

        self.index = AnnoyIndex(emb_size)

        # Populate the search index with the trained embedding
        for row in range(0, nrows):
            vector = list(entities_matrix[row])
            self.index.add_item(row, vector)

        # Generate the index itself. This may take long time
        self.index.build(depth)

        # Index ready
        self.ready = True

    def save_to_binary(self, filepath):
        """Dump the search tree on a file on disk

        :param string filepath: The path where the file will be saved
        :return: If operations had or not errors
        :rtype: boolean
        """
        if self.index is None or self.ready is False:
            print("The index is not ready to be saved")
            return False

        self.index.save(filepath)
        return True

    def load_from_file(self, filepath, emb_size):
        """Load the search tree from a file on disk

        :param string filepath: The path where the file will be saved
        :param int emb_size: The size of embedding vector used
        :return: If operations had or not errors
        :rtype: boolean
        """
        self.index = AnnoyIndex(emb_size)
        self.index.load(filepath)
        self.ready = True


if __name__ == '__main__':

    print("This is server module")
