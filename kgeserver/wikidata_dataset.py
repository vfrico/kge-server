#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# WikidataDataset Class: Creates a data set from Wikidata
# Copyright (C) 2016 - 2017 Víctor Fernández Rico <vfrico@gmail.com>
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
import collections
import logging
import time


class WikidataDataset(kgeserver.dataset.Dataset):
    def __init__(self, sparql_endpoint=None, thread_limiter=4):
        """Creates WikidataDataset class

        The default endpoint is the original from wikidata.

        :param string new_endpoint: The URI of the SPARQL endpoint
        :param integer thread_limiter: The number of concurrent HTTP queries
        """
        super(WikidataDataset, self).__init__(sparql_endpoint=sparql_endpoint,
                                              thread_limiter=thread_limiter)
        # Compile regex to better performance
        self.chk_digit = re.compile('\d')

        # Save all entities already explored by process_entity (saves time)
        self.entities_explored = {}

        # TODO: May be useful save these uri's on dataset binary?
        # Used as constants to get entity or get prop
        self.entity_base = "http://www.wikidata.org/entity/"
        self.relation_base = "http://www.wikidata.org/prop/"

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
            entity_uri = entity.split("/")
            wikidata_id = entity_uri[-1]

            # The last uri number should start with Q and has entity keyword
            # Number after Q must be a valid integer
            if wikidata_id[0] is "Q" and entity_uri[-2] == 'entity' and\
               self.chk_digit.search(wikidata_id[1:]):
                return wikidata_id
            else:
                return None
        except Exception:
            # The entity is also valid if element is "Q1234"
            if entity[0] is "Q" and\
               self.chk_digit.search(entity[1:]):
                return entity
            else:
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
            prp_uri = relation.split("/")
            wikidata_prop = prp_uri[-1]

            # The last uri number should start with P and has prop,
            # direct or statement keyword. Number after P also should be valid
            if wikidata_prop[0] is "P" and prp_uri[3] == 'prop' and\
               (prp_uri[4] == "direct" or prp_uri[4] == "statement" or
                prp_uri[-1] == prp_uri[4])\
               and self.chk_digit.search(wikidata_prop[1:]):
                return wikidata_prop
            else:
                return None
        except Exception:
            # The Prop is also valid if it starts with P with number. ie: 'P53'
            if relation[0] is "P" and\
               self.chk_digit.search(relation[1:]):
                return relation
            else:
                return None
        return None

    def get_entity_id(self, entity):
        """Gets the id given an entity

        :param string entity: The entity string
        """
        try:
            entity = self.check_entity(entity)
            return self.entities_dict[entity]
        except (KeyError, ValueError):
            return None

    def get_entity(self, id):
        """Gets the entity URI given an id

        :param integer id: The id to find
        """
        try:
            return self.entity_base + self.entities[id]
        except ValueError:
            return None

    def get_relation(self, id):
        """Gets the relation URI given an id

        :param int id: The relation identifier to find
        """
        try:
            return self.relation_base + self.relations[id]
        except ValueError:
            return None

    def get_relation_id(self, relation):
        """Gets the id given an relation

        :param string entity: The relation string
        """
        try:
            relation = self.check_relation(relation)
            return self.relations_dict[relation]
        except (KeyError, ValueError):
            return None

    def extract_entity(self, entity,
                       filters={'wdt-entity': True, 'wdt-reference': False,
                                'wdt-statement': False, 'wdt-prop': True,
                                'literal': False, 'bnode': False}):
        """Given an entity, returns the valid representation, ready to be saved

        The filter argument allows to avoid adding elements into lists that
        will not be used. It is a dictionary with the shape: {'filter': bool}.
        The valid filters (and default) are:
            * *wdt-entity* - True
            * *wdt-reference* - False
            * *wdt-statement* - True
            * *wdt-prop* - True
            * *literal* - False
            * *bnode* - False

        :deprecated: -> Must be implemented in child class
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

    def get_seed_vector(self, verbose=0, where="?subject wdt:P950 ?bne ."):
        """Auxiliar method that outputs a list of seed elements

        This seed vector will be the 'root nodes' of a tree with the
        desired depth on parent class (`load_dataset_recurrently`)

        :param verbose: The desired level of verbosity
        :param string where: SPARQL where to construct query
        :return: A list of entities
        :rtype: list
        """
        # Count all Wikidata elements with a BNE entry
        count_query = """
            PREFIX wikibase: <http://wikiba.se/ontology>
            SELECT (count(DISTINCT ?subject) as ?count)
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

        limit = 5000
        seed_vector = []
        # fill a list with wikidata entries related to BNE elements
        for q in range(0, math.ceil(entities_number / limit)):
            offset = q * limit
            first_query = """
                PREFIX wikibase: <http://wikiba.se/ontology>
                SELECT DISTINCT ?subject
                WHERE {{
                    {2}
                }} LIMIT {0} OFFSET {1}
                """.format(limit, offset, where)
            if verbose > 2:
                print("The first query is: \n", first_query)
            sts, first_json = self.execute_query(first_query)
            if verbose > 2:
                print(sts, len(first_json))
            seed_vector += [entity['subject']['value']
                            for entity in first_json]
        return seed_vector

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
            PREFIX wikibase: <http://wikiba.se/ontology>
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
                PREFIX wikibase: <http://wikiba.se/ontology>
                SELECT ?subject ?object ?predicate
                WHERE {{
                    {2}
                }} LIMIT {0} OFFSET {1}
                """.format(limit, offset, where)
            if verbose > 2:
                print("The first query is: \n", first_query)
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
                        graph_pattern=("{0} ?predicate ?object . "
                                       "?predicate a owl:ObjectProperty . "
                                       "FILTER NOT EXISTS {{ "
                                       "?object a wikibase:BestRank }}")
                        ):
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

        # Extract correctly the id of the wikidata element.
        try:
            # If either fails to convert the last Q number into int
            # or the URI hasn't 'entity' keyword, returns without doing nothing
            wikidata_id = int(self.check_entity(entity)[1:])
        except Exception:
            return False

        wdt_entity = "wd:Q{0}".format(wikidata_id)
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

    def entity_labels(self, entity, langs=['es', 'en'], tries=1):
        """Saves the label for a given entity

        Makes a SPARQL query to retrieve the entity's label(s) requested to use
        them on other services.

        Some SPARQL endpoints may return more languages than requested. E.g:
        Wikidata will return 'en-ca', 'en-gb', 'en-us' and more if available
        when 'en' has been requested. Those languages will also be returned
        on this function.

        Sample call: `wd.entity_labels("Q1", langs=['en', 'es'])`
        Sample return value: {'en-ca': 'universe', 'es': 'universo',
                              'en-gb': 'universe', 'en': 'universe'}

        :param string entity: The entity to query for
        :param list langs: The languages to be asked for
        :return: The label on each requested language
        :rtype: lang
        """
        VAR_LABEL = "label"
        VAR_DESCRIPTION = "description"
        VAR_ALTLABEL = "altLabel"
        LANG_SELECTOR = 'LANGMATCHES(LANG(?{var}), "{language}")'
        # Create the FILTER section (to choose which langs to query)
        l_label = " || ".join([LANG_SELECTOR.format(language=lang,
                              var=VAR_LABEL) for lang in langs])
        l_desc = " || ".join([LANG_SELECTOR.format(language=lang,
                             var=VAR_DESCRIPTION) for lang in langs])
        l_alt = " || ".join([LANG_SELECTOR.format(language=lang,
                            var=VAR_ALTLABEL) for lang in langs])
        # print(l_label, l_desc)
        label_query = """SELECT ?{1} ?{3} ?{5}
            WHERE {{
                wd:{entity} rdfs:label ?{1} . FILTER({0}) .
                OPTIONAL {{
                    wd:{entity} schema:description ?{3} .  FILTER({2}) .
                }} OPTIONAL {{
                    wd:{entity} skos:altLabel ?{5} .  FILTER({4}) .
                }}
        }}""".format(l_label, VAR_LABEL,
                     l_desc, VAR_DESCRIPTION,
                     l_alt, VAR_ALTLABEL, entity=entity)
        try:
            # Perform the query
            http_status, json_response = self.execute_query(label_query)
            if http_status != 200:
                logging.error(("HTTP Status {} is not correct. \n\n"
                               "Query executed:\n {}\n\n"
                               "Response:\n {}\n\n").format(http_status,
                                                            label_query,
                                                            json_response))
                return {}, {}, {}
                # raise kgeserver.dataset.ExecuteQueryError(
                #     "HTTP Status {} is not correct".format(http_status))

            # Build the result dict and return it
            labels = {}
            descriptions = {}
            # A single entity could have multiple alt_labels
            alt_labels = collections.defaultdict(set)
            for row in json_response:
                try:
                    labels[row[VAR_LABEL]['xml:lang']] = row[VAR_LABEL]['value']
                except KeyError:
                    pass

                try:
                    descriptions[row[VAR_DESCRIPTION]['xml:lang']] =\
                        row[VAR_DESCRIPTION]['value']
                except KeyError:
                    pass

                try:
                    # If language is not available or is empty, return empty
                    alt_labels[row[VAR_ALTLABEL]['xml:lang']].add(
                        row[VAR_ALTLABEL]['value'])
                except KeyError:
                    pass

            # Using a set avoids duplicated strings, but need a conversion
            for lang in alt_labels:
                alt_labels[lang] = list(alt_labels[lang])

            return labels, descriptions, dict(alt_labels)
        except Exception as exc:
            if tries <= 10:
                time.sleep(30)  # Wait some time if error dismiss
                tries += 1
                return entity_labels(entity, langs, tries)
            else:
                raise kgeserver.dataset.MaxTriesExceededError(
                    "Tried {} times".format(tries))

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
        """Extract triplets from a statement

        Should receive the entity which is the subject of the triple and
        the uri of the statement

        :param string entity: The entity whic statement is related
        :param string uri: The uri of the statement
        :return: The entities statement is related
        :rtype: list
        """
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
            # If the object on the relation is an entity, save the triple and
            # return the entity into a list
            pred_uri = (elem['pred']['value'])
            subj_uri = (elem['subj']['value'])

            subj = self.check_entity(subj_uri)

            if subj:
                el_queue.append(subj_uri)
                self.add_triple(entity, subj_uri, pred_uri)

        return el_queue
