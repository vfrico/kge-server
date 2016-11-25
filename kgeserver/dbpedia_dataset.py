#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# WikidataDataset Class: Creates a data set from Wikidata
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

import kgeserver
import kgeserver.dataset
import re
import math


class ESDBpediaDataset(kgeserver.dataset.Dataset):
    def __init__(self, thread_limiter=32):
        """Creates WikidataDataset class

        The default endpoint is the original from wikidata.

        :param string new_endpoint: The URI of the SPARQL endpoint
        :param integer thread_limiter: The number of concurrent HTTP queries
        """
        sparql_endpoint = "http://es.dbpedia.org/sparql?query="
        super(ESDBpediaDataset, self).__init__(sparql_endpoint=sparql_endpoint,
                                               thread_limiter=thread_limiter)

        # Save all entities already explored by process_entity (saves time)
        self.entities_explored = {}

    def check_entity(self, entity):
        # Example http://es.dbpedia.org/resource/Siemens_Velaro
        try:
            entity_uri = entity.split("/")
            dbpedia_id = entity_uri  # Returns the entire URI

            # The last uri number should start with Q and has entity keyword
            # Number after Q must be a valid integer
            if entity_uri[-2] == 'resource' and\
               entity_uri[2] == 'es.dbpedia.org':
                # print("Entity", entity, True)
                return entity
            else:
                # print("Entity", entity, False)
                return None
        except (ValueError, IndexError):
            # print("Entity", entity, False)
            return None
        # print("Entity", entity, False)
        return None

    def check_relation(self, relation):
        # Example http://es.dbpedia.org/property/vmax
        # http://es.dbpedia.org/ontology/wikiPageRedirects
        # http://xmlns.com/foaf/0.1/isPrimaryTopicOf
        # http://www.w3.org/2002/07/owl#sameAs
        # http://www.w3.org/2000/01/rdf-schema#label
        try:
            entity_uri = relation.split("/")
            dbpedia_id = entity_uri

            # The last uri number should start with Q and has entity keyword
            # Number after Q must be a valid integer
            if (entity_uri[-2] == 'property' and
               entity_uri[-1] != "wikiPageWikiLink") or\
               (entity_uri[-2] == 'ontology' and
               entity_uri[-1] != "wikiPageWikiLink") or\
               entity_uri[2] == 'xmlns.com' or\
               entity_uri[2] == 'www.w3.org':
                # print("relation:", relation, True)
                return relation
            else:
                # print("relation1:", relation, False)
                return None
        except (ValueError, IndexError):
            # print("relation2:", relation, False)
            return None
        # print("relation3:", relation, False)
        return None

    def load_from_graph_pattern(self, verbose=0, where="", **kwargs):
        """Auxiliar method that outputs a list of seed elements

        This seed vector will be the 'root nodes' of a tree with the
        desired depth on parent class (`load_dataset_recurrently`)

        :param verbose: The desired level of verbosity
        :param string where: SPARQL where to construct query
        :param int batch_size: The size of batches queried each time
        :return: A list of entities
        :rtype: list
        """
        # Count all Wikidata elements
        count_query = """
            PREFIX dcterms: <http://purl.org/dc/terms/>
            SELECT (count(*) as ?count)
            WHERE {{
                {0}
            }}""".format(where)

        if verbose > 2:
            print("The count query is: \n", count_query)
        sts, count_json = self.execute_query(count_query)
        if verbose > 2:
            print(sts, count_json)

        # The number of elements
        entities_number = int(count_json[0]['count']['value'])

        if verbose > 0:
            print("Found {} entities".format(entities_number))

        if 'batch_size' in kwargs:
            limit = kwargs['batch_size']
        else:
            limit = 100000

        seed_vector = []
        rounds_number = math.ceil(entities_number / limit)
        print("Hay {} tripletas, se van a hacer {} consultas".format(
            entities_number, rounds_number))
        if 'start_callback' in kwargs:
            kwargs['start_callback'](rounds_number)
        for q in range(0, rounds_number):
            offset = q * limit
            first_query = """
                PREFIX dcterms: <http://purl.org/dc/terms/>
                SELECT ?subject ?object ?predicate
                WHERE {{
                    {2}
                }} LIMIT {0} OFFSET {1}
                """.format(limit, offset, where)
            if verbose > 2:
                print("The query is: \n", first_query)
            self.load_dataset_from_query(first_query)
            self.show()
            if 'callback' in kwargs:
                kwargs['callback']()
            # sts, first_json = self.execute_query(first_query)
            # if verbose > 2:
            #     print(sts, len(first_json))
            # seed_vector += [entity['subject']['value']
            #                 for entity in first_json]
        return self.entities

    def _process_entity(self, entity, verbose=0,
                        graph_pattern=("{0} ?predicate ?object . ")):
        """Take entity and explore all relations and entities related to it

        This will execute the SPARQL query with the params passed to
        build a dataset with the *object* elements on triples retrieved
        from the server.

        :return: A list with new entities to be scanned
        """
        # Check first if entity has been already explored
        if self.exist_element(self.check_entity(entity),
                              self.entities_explored):
            return False

        wdt_entity = "<{0}>".format(entity)
        el_query = """SELECT ({1} as ?subject) ?predicate ?object
            WHERE {{
              {0}
            }}""".format(graph_pattern.format(wdt_entity),
                         wdt_entity)
        if verbose > 2:
            print("The element query is: \n", el_query)
        # Get all related elements
        sts, el_json = self.execute_query(el_query)
        if verbose > 2:
            print("HTTP", sts, len(el_json))

        # Check future errors
        if sts is not 200:
            return False

        # Mark entity as already explored
        self.entities_explored[self.check_entity(entity)] = True

        # Entities to be explored next level
        to_queue = []

        # For related elements, get all relations and objects
        for relation in el_json:
            try:
                object_uri = relation['object']['value']

                # Add the subject scanned only if is valid
                obj = self.check_entity(object_uri)

                if obj:
                    to_queue.append(object_uri)

                # Add triple will ensure every elements are valid
                self.add_triple(entity, relation['object']['value'],
                                relation['predicate']['value'])

            except KeyError:
                print("Error on relation: {}".format(relation))
                return False

        return to_queue
