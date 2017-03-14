#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# search_dao.py: Manages elasticsearch access to search entities
# Copyright (C) 2017 Víctor Fernández Rico <vfrico@gmail.com>
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

import os
import redis
import json
from elasticsearch import Elasticsearch
import kgeserver.dataset as dataset
import kgeserver.wikidata_dataset as wikidata_dataset
# import data_access.data_access_base as data_access_base


class EntityDAO():
    def __init__(self):
        """
        """
        # TODO: Generate an index on elasticsearch with allowed fields
        # The entity must be loaded with a dataset

        # Elasticsearch global params
        self.ELASTIC_ENDPOINT = "http://elasticsearch:9200/"
        self.ELASTIC_AUTH = ("elastic", "changeme")

        # Create Elasticsearch object
        self.es = Elasticsearch(self.ELASTIC_ENDPOINT,
                                http_auth=self.ELASTIC_AUTH)

    def generate_index(self, indexName):
        body = {'mappings': {'WikidataDataset': {'properties': {}}}}
        entity = {'type': 'string'}
        suggest_field = {
            'type': 'completion',
            'analyzer': 'standard',
            'search_analyzer': 'standard',
            'preserve_separators': False,
            'preserve_position_increments': False
        }
        body['mappings']['WikidataDataset']['properties'] = {
            "entity": entity,
            "label_suggest": suggest_field
        }
        print(body)
        self.es.indices.create(index=indexName, body=body)

    def suggest_entity(self, input_string):
        # TODO: Make a query to elasticsearch to find what the user wants
        pass

    def insert_entity(self, entity):
        # TODO: Insert information of an entity
        pass
