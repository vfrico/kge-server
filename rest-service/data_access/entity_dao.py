#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# entity_dao.py: Manages elasticsearch access to search entities
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
import uuid
import elasticsearch.exceptions as es_exceptions
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
        self.index = "entities"
        self.type = "WikidataDataset"
        # Test if index exists, and if not, creates it
        if not self.es.indices.exists(index=self.index):
            self.generate_index(self.index)

    def generate_index(self, indexName):
        body = {'mappings': {
                            'WikidataDataset': {
                                'properties': {},
                                'dynamic': True
                                }
                             },
                'settings': {
                    'analysis': {
                      'analyzer': {
                        'my_custom_analyzer': {
                          'type': 'custom',
                          'tokenizer': 'standard',
                          'filter': ['lowercase', 'my_ascii_folding']
                        }
                      },
                      'filter': {
                        'my_ascii_folding': {
                            'type': 'asciifolding',
                            'preserve_original': True
                        }
                      }
                    }
                  }}
        suggest_field = {
            'type': 'completion',
            'analyzer': 'my_custom_analyzer',
            'search_analyzer': 'standard',
            'preserve_separators': False,
            'preserve_position_increments': False
        }
        body['mappings']['WikidataDataset']['properties'] = {
            'entity': {'type': 'string'},
            'description': {'type': 'object'},
            'label': {'type': 'object'},
            'label_suggest': suggest_field
        }
        try:
            self.es.indices.delete(index=indexName)
        except es_exceptions.NotFoundError:
            pass
        self.es.indices.create(index=indexName, body=body)

    def suggest_entity(self, input_string):
        """
        Must return a list of entities
        """
        # Make a query to elasticsearch to find what the user wants
        request = {
          "entities": {
            "text": input_string,
            "completion": {
                "field": "label_suggest"
            }
          }
        }
        resp = self.es.suggest(index=self.index, body=request)
        # print(resp)
        return resp

    def insert_entity(self, entity):
        # Entity document which will be stored on elasticsearch
        full_doc = {"entity": entity['entity'],
                    "description": entity['description'],
                    "label": entity['label'],
                    "label_suggest": list(entity['label'].values())
                    }
        # print(full_doc)
        return self.es.create(index=self.index, doc_type=self.type,
                              body=full_doc, id=str(uuid.uuid4()))
