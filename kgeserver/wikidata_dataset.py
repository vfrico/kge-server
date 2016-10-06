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
import re


class WikidataDataset(kgeserver.dataset.Dataset):
    def __init__(self, sparql_endpoint=None, thread_max=32):
        """Creates WikidataDataset class"""
        super(WikidataDataset, self).__init__(new_endpoint=sparql_endpoint,
                                              thread_limiter=thread_max)
        # Compile regex to better performance
        self.chk_digit = re.compile('\d')
        self.entities_explored = {}

    def check_entity(self, entity):
        """Check the entity given and return a valid representation

        :param string entity: The input entity representation
        :return: A valid representation or None
        :rtype: string
        """
        # This expects as input an entity URI
        # http://www.wikidata.org/entity/Q180
        # http://www.wikidata.org/entity/Q42

        try:
            # If either fails to convert the last Q number into int
            # or the URI hasn't 'entity' keyword, returns without doing nothing
            entity_uri = entity.split("/")
            wikidata_id = entity_uri[-1]
            # print(entity, wikidata_id)
            if wikidata_id[0] is "Q" and entity_uri[-2] == 'entity' and\
               self.chk_digit.search(wikidata_id[1:]):
                # print(True, wikidata_id)
                return wikidata_id
            else:
                # print("elsetry")
                return None
        except Exception:
            # The entity seems not to be an URI
            if entity[0] is "Q" and\
               self.chk_digit.search(entity[1:]):
                # print(True, entity)
                return entity
            else:
                # print("elseexcept")
                return None
        # print("ret")
        return None

    def check_relation(self, relation):
        """Check the relation given and return a valid representation

        :param string relation: The input relation representation
        :return: A valid representation or None
        :rtype: string
        """
        # http://www.wikidata.org/prop/direct/P2853 VALID
        # http://www.wikidata.org/prop/statement/P159 VALID
        # http://www.wikidata.org/prop/P373 VALID
        # http://www.wikidata.org/prop/qualifier/P18 NOT VALID

        try:
            # If either fails to convert the last Q number into int
            # or the URI hasn't 'entity' keyword, returns without doing nothing
            prp_uri = relation.split("/")
            wikidata_prop = prp_uri[-1]

            if wikidata_prop[0] is "P" and prp_uri[3] == 'prop' and\
               (prp_uri[4] == "direct" or prp_uri[4] == "statement" or
                prp_uri[-1] == prp_uri[4])\
               and self.chk_digit.search(wikidata_prop[1:]):
                return wikidata_prop
            else:
                return None
        except Exception:
            # The relation seems not to be an URI
            if relation[0] is "P" and\
               self.chk_digit.search(relation[1:]):
                return relation
            else:
                return None
        return None

    def extract_entity(self, entity,
                       filters={'wdt-entity': True, 'wdt-reference': False,
                                'wdt-statement': False, 'wdt-prop': True,
                                'literal': False, 'bnode': False}):
        """Given an entity, returns the valid representation, ready to be saved

        Going to be deprecated -> Must be implemented in child class

        The filter argument allows to avoid adding elements into lists that
        will not be used. It is a dictionary with the shape: {'filter': bool}.
        The valid filters (and default) are:
            * *wdt-entity* - True
            * *wdt-reference* - False
            * *wdt-statement* - True
            * *wdt-prop* - True
            * *literal* - False
            * *bnode* - False

        :param dict entity: The entity to be analyzed
        :param dict filters: A dictionary to allow filter entities
        :return: The entity itself or False
        """

        if entity["type"] == "uri":
            # Not all 'uri' values are valid entities
            try:
                uri = entity["value"].split('/')
                if uri[2] == 'www.wikidata.org' and \
                        (uri[3] == "reference" and filters['wdt-reference']):
                    return entity["value"]
                elif uri[2] == 'www.wikidata.org' and \
                        (uri[4] == "statement" and filters['wdt-statement']):
                    return entity["value"]
                elif uri[2] == 'www.wikidata.org' and \
                        (uri[3] == "entity" and filters['wdt-entity']) and \
                        not uri[4] == "statement":
                    return entity["value"]
                elif uri[2] == 'www.wikidata.org' and \
                        (uri[3] == "prop" and filters['wdt-prop']):
                    return entity["value"]
                elif uri[2] == 'www.wikidata.org':
                    return False
                else:
                    # Only discards certain Wikidata urls, the rest are valid
                    return entity["value"]
            except IndexError:
                return False

        elif entity["type"] == "literal" and filters['literal']:
            return entity
        elif entity["type"] == "bnode" and filters['literal']:
            return entity
        else:
            return False

    def get_seed_vector(self, verbose=0):
        """Auxiliar method that outputs a list of seed elements

        This seed vector will be the 'root nodes' of a tree with the
        desired depth on parent class (`load_dataset_recurrently`)

        :param verbose: The desired level of verbosity
        :return: A list of entities
        :rtype: list
        """
        # Count all Wikidata elements with a BNE entry
        count_query = """
            PREFIX wikibase: <http://wikiba.se/ontology>
            SELECT (count(distinct ?wikidata) as ?count)
            WHERE {
                ?wikidata wdt:P950 ?bne .
            }"""

        if verbose > 2:
            print("The count query is: \n", count_query)
        sts, count_json = self.execute_query(count_query)
        if verbose > 2:
            print(sts, count_json)

        # The number of elements
        entities_number = int(count_json[0]['count']['value'])

        if verbose > 0:
            print("Found {} entities".format(entities_number))

        # fill a list with wikidata entries related to BNE elements
        first_query = """
            PREFIX wikibase: <http://wikiba.se/ontology>
            SELECT ?wikidata
            WHERE {
                ?wikidata wdt:P950 ?bne .
            }
            """
        if verbose > 2:
            print("The first query is: \n", first_query)
        sts, first_json = self.execute_query(first_query)
        if verbose > 2:
            print(sts, len(first_json))

        return [entity['wikidata']['value'] for entity in first_json]

    # def _process_entity(self, entity, verbose=0):

        # twolevel_query = """
        # SELECT (wd:Q180 as ?object) ?predicate ?subject ?pred ?subj
        # WHERE {
        #   ?predicate a owl:ObjectProperty .
        #   wd:Q180 ?predicate ?subject .
        #   FILTER NOT EXISTS { ?subject a wikibase:BestRank }
        # }
        # """

    def _process_entity(self, entity, verbose=0):
        """
        :return: A list with new entities to be scanned
        """
        # Check first if entity has been already explored
        if self.exist_element(self.check_entity(entity),
                              self.entities_explored):
            return False

        # Extract correctly the id of the wikidata element.
        try:
            # If either fails to convert the last Q number into int
            # or the URI hasn't 'entity' keyword, returns without doing nothing
            wikidata_id = int(entity.split("/")[-1][1:])
            if not entity.split("/")[-2] == 'entity':
                raise Exception
        except Exception:
            return False

        el_query = """SELECT (wd:Q{0} as ?object) ?predicate ?subject
                WHERE {{
                  ?predicate a owl:ObjectProperty .
                  wd:Q{0} ?predicate ?subject .
                  FILTER NOT EXISTS {{ ?subject a wikibase:BestRank }}
                }}
            """.format(wikidata_id)
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

        # Add element to entities queue
        # id_obj = self.add_element(entity, self.entities, self.entities_dict)
        to_queue = []

        # For related elements, get all relations and objects
        for relation in el_json:

            try:
                subject_uri = relation['subject']['value']
                # if relation['subject']['type'] == "uri" and self.is_statement(subject_uri):
                #     # Do queries to extract relations on statements
                #     new_triples = self.extract_from_statement(entity, subject_uri)
                #     # if new_triples:
                #     #     print(new_triples)
                #     to_queue.append(new_triples)

                subj = self.check_entity(subject_uri)

                # if subj and not self.exist_element(subj, self.entities_dict):
                #     to_queue.append(subject_uri)
                if subj:
                    to_queue.append(subject_uri)

                added = self.add_triple(entity, relation['subject']['value'],
                                        relation['predicate']['value'])
                # print("It was added {}".format(added))

            except KeyError:
                print("Error on relation: {}".format(relation))
                return False

        return to_queue

    def is_statement(self, uri):
        """Check if an URI is a wikidata statement

        :param string uri: The uri to test
        :return: If it is an uri or not
        :rtype: boolean
        """
        # print("The uri {} can be a statement".format(uri))
        try:
            l_uri = uri.split("/")
            return l_uri[-2] == 'statement' and l_uri[-3] == 'entity'
        except Exception:
            return False

    def extract_from_statement(self, entity, uri):
        # print("The uri {} is a statement".format(uri))
        st_query = """PREFIX wikibase: <http://wikiba.se/ontology>
          SELECT ?pred ?subj
          WHERE {{
          <{0}> ?pred ?subj .
          }}""".format(uri)

        sts, el_json = self.execute_query(st_query)
        # print(sts, el_json)
        # Check errors
        if sts is not 200:
            return None

        el_queue = []

        for elem in el_json:
            pred_uri = (elem['pred']['value'])
            subj_uri = (elem['subj']['value'])

            subj = self.check_entity(subj_uri)

            if subj and not self.exist_element(subj, self.entities_dict):
                el_queue.append(subj_uri)

            added = self.add_triple(entity, subj_uri, pred_uri)
            # print("Relation from statement added {}".format(added))

        return el_queue
