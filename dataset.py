import requests
import json
import pickle
import numpy as np
import threading
from queries import Queries
from datetime import datetime
import time


class Dataset():
    WIKIDATA_ENDPOINT = \
        """https://query.wikidata.org/bigdata/namespace/wdq/sparql?query="""
    entities = []
    entities_dict = {}
    relations = []
    relations_dict = {}
    subs = []

    # Used to show current status
    status = {'started': 0,
              'round_curr': 0,
              'round_total': 0,
              'it_analyzed': 0,
              'it_total': 0,
              'active': False}

    def __init__(self, new_endpoint=None, thread_limiter=32):
        """Creates the dataset class

        The default endpoint is the original from wikidata.
        :param str new_endpoint: The URI of the SPARQL endpoint
        :param int thread_limiter: The number of concurrent HTTP queries
        """
        if new_endpoint is not None:
            self.WIKIDATA_ENDPOINT = new_endpoint

        self.th_semaphore = threading.Semaphore(thread_limiter)
        self.query_sem = threading.Semaphore(thread_limiter)

    def show(self, verbose=False):
        """Show all elements of the dataset

        By default prints only one line with the number of entities, relations
        and triplets. If verbose, prints every list. Use wisely

        :param bool verbose: If true prints every item of all lists
        """
        print("%d entities, %d relations, %d tripletas" %
              (len(self.entities), len(self.relations), len(self.subs)))
        if verbose is True:
            print("\nEntities (%d):" % len(self.entities))
            for entity in self.entities:
                print(entity)
            print("\nRelations (%d):" % len(self.relations))
            for relation in self.relations:
                print(relation)
            print("\nTripletas (%d):" % len(self.subs))
            for sub in self.subs:
                print(sub)

    def add_element(self, element, complete_list,
                    complete_list_dict, only_uri=False):
        """Add element to a list of the dataset. Avoids duplicate elements.

        :param str element: The element that will be added to list
        :param list complete_list: The list in which will be added
        :param dict complete_list_dict: The dict which represents the list.
        :param bool only_uri: Allow load objects distincts than URI's
        :return: The id on the list of the added element
        :rtype: int
        """

        # An URI is a string type
        if only_uri is True and not isinstance(element, str):
            return False
        elif element is False:
            return False

        try:
            # Item is on the list, return same id
            return complete_list_dict[element]

        except (KeyError, ValueError):
            # Item is not on the list, append and return id
            complete_list.append(element)
            id_item = len(complete_list)-1
            complete_list_dict[element] = id_item
            return id_item

    def exist_element(self, element, complete_list_dict):
        """Check if element exists on a given list

        :param str element: The element itself
        :param dict complete_list_dict: The dictionary to search in
        :return: Wether the item was found or no
        :rtype: bool
        """
        try:
            # Item is on the list, return same id
            elem_id = complete_list_dict[element]
            return True

        except (KeyError, ValueError):
            # Item is not on the list
            return False

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
                        (uri[3] == "entity" and filters['wdt-entity']):
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

    def load_dataset_from_json(self, json, only_uri=False):
        """Loads the dataset object with a JSON

        The JSON structure required is:
        {'object': {}, 'subject': {}, 'predicate': {}}

        :param list json: A list of dictionary parsed from JSON
        :param bool only_uri: Allow load objects distincts than URI's
        """

        for tripl in json:
            id_obj = self.add_element(self.extract_entity(tripl["object"]),
                                      self.entities, self.entities_dict,
                                      only_uri=only_uri)
            id_subj = self.add_element(self.extract_entity(tripl["subject"]),
                                       self.entities,
                                       self.entities_dict, only_uri=only_uri)
            id_pred = self.add_element(self.extract_entity(tripl["predicate"]),
                                       self.relations,
                                       self.relations_dict, only_uri=only_uri)

            if id_obj is False or id_subj is False or id_pred is False:
                continue
            else:
                self.subs.append((id_obj, id_subj, id_pred))

    def load_dataset_from_query(self, query, only_uri=False):
        """Receives a Sparql query and fills dataset object with the response

        The method will execute the query itself and will call to other method
        to fill in the dataset object

        :param str query: A valid SPARQL query
        :param bool only_uri: Allow load objects distincts than URI's
        """

        result_query = self.execute_query(query)
        if result_query[0] is not 200:
            raise Exception("Error on endpoint. HTTP status code: " +
                            str(response.status_code))
        else:
            jsonlist = result_query[1]
        # print(json.dumps(jsonlist, indent=4, sort_keys=True))
        self.load_dataset_from_json(jsonlist, only_uri=only_uri)

    def load_dataset_from_nlevels(self, nlevels,
                                  extra_params="", only_uri=False):
        """Builds a nlevels query, executes, and loads data on object

        :deprecated:
        :param int nlevels: Deep of the search on wikidata graph
        :param str extra_params: Extra SPARQL instructions for the query
        :param bool only_uri: Allow load objects distincts than URI's
        """

        query = self.build_n_levels_query(nlevels)+" "+extra_params
        print(query)
        return self.load_dataset_from_query(query, only_uri=only_uri)

    def build_levels(self, n_levels):
        """Generates a simple *chain* of triplets for the desired levels

        :param int n_levels: Deep of the search on wikidata graph
        :return: A list of chained triplets
        :rtype: list
        """

        ob1 = "wikidata"
        pre = "predicate"
        ob2 = "object"
        pre_base = pre
        obj_base = ob2
        predicateCount = 1
        objectCount = 1

        tripletas = []

        for level in range(1, n_levels+1):
            tripletas.append((ob1, pre, ob2))
            objectCount += 1
            predicateCount += 1
            ob1 = ob2
            ob2 = obj_base + str(objectCount)
            pre = pre_base + str(predicateCount)

        return tripletas

    def build_n_levels_query(self, n_levels=3):
        """Builds a CONSTRUCT SPARQL query of the desired deep

        :param int n_levels: Deep of the search on wikidata graph
        :return: The desired chained query
        :rtype: string
        """

        lines = []
        for level in self.build_levels(n_levels):
            lines.append("?"+level[0]+" ?"+level[1]+" ?"+level[2])

        query = """PREFIX wikibase: <http://wikiba.se/ontology>
            construct {{ {0} }}
            WHERE {{ ?wikidata wdt:P950 ?bne .
            {1}
            }} """.format(" . ".join(lines), " . \n".join(lines))

        return query

    def __all_entity_triplet__(self, element,
                               append_queue=lambda: None, verbose=0,
                               callback=lambda: None):
        """Add to dataset all the relations from an entity

        This method is runned for one thread. It will check if the Wikidata
        entity is valid, make a SPARQL query and save all triplets on the
        dataset.
        :param str element: The URI of element to be scanned
        :param function append_queue: A function that receives the subject of
                                      a triplet as an argument
        :param int verbose: The level of verbosity. 0 is low, and 2 is high
        :return: Nothing
        """

        # Extract correctly the id of the wikidata element.
        try:
            # If either fails to convert the last Q number into int
            # or the URI hasn't 'entity' keyword, returns without doing nothing
            wikidata_id = int(element.split("/")[-1][1:])
            assert element.split("/")[-2] == 'entity'
        except Exception:
            callback()

        el_query = """PREFIX wikibase: <http://wikiba.se/ontology>
            SELECT ?predicate ?object
            WHERE {{
                wd:Q{0} ?predicate ?object .
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
            callback()

        # Add element to entities queue
        id_obj = self.add_element(element, self.entities, self.entities_dict)

        # For related elements, get all relations and objects
        for relation in el_json:
            pred = self.extract_entity(relation['predicate'])
            obj = self.extract_entity(relation['object'])

            if pred is not False and obj is not False:
                # Add to the queue iff the element hasn't been scanned
                if not self.exist_element(obj, self.entities_dict):
                    append_queue(obj)

                # Add relation
                id_pred = self.add_element(pred, self.relations,
                                           self.relations_dict)
                id_subj = self.add_element(obj, self.entities,
                                           self.entities_dict)
                if id_subj is not False or id_pred is not False:
                    self.subs.append((id_obj, id_subj, id_pred))

        callback()

    def load_dataset_recurrently(self, levels, verbose=1):
        """Loads to dataset all entities with BNE ID and their relations

        Due to Wikidata endpoint cann't execute queries that take long time
        to complete, it is necessary to consruct the dataset entity by entity,
        without using SPARQL CONSTRUCT. This method will start concurrently
        some threads to make several SPARQL SELECT queries.

        :param int levels: The depth to get triplets related with original item
        :param int verbose: The level of verbosity. 0 is low, and 2 is high
        :return: True if operation was successful
        :rtype: bool
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

        # Create a queue for wikidata elements to be scanned
        new_queue = [entity['wikidata']['value'] for entity in first_json]
        el_queue = []

        if verbose > 1:
            status_thread = None

            # Initialize status variables
            self.status['started'] = datetime.now()
            self.status['it_analyzed'] = 0
            self.status['active'] = True
            self.status['round_total'] = levels
            status_thread = threading.Thread(
                target=self.__control_thread__,
                args=(),)
            status_thread.start()

        # Loop for depth levels
        for level in range(0, levels):
            # Loop for every item on the queue
            if verbose > 0:
                print("Scanning level {} with {} elements"
                      .format(level+1, len(new_queue)))
            el_queue = new_queue
            new_queue = []

            # Initialize some status variables
            self.status['round_curr'] = level
            self.status['it_total'] = len(el_queue)

            # pool for threads
            threads = []

            # Scan every entity on queue
            for element in el_queue:
                # Generate n threads, start them and save into pool

                def func_callback():
                    self.status['it_analyzed'] += 1
                    self.th_semaphore.release()

                self.th_semaphore.acquire()
                t = threading.Thread(
                    target=self.__all_entity_triplet__,
                    args=(element, ),
                    kwargs={'verbose': verbose,
                            'append_queue': lambda e: new_queue.append(e),
                            'callback': func_callback})
                threads.append(t)
                t.start()

            if verbose > 0:
                print("Waiting all threads to end")
            # Wait for threads to end
            for th in threads:
                th.join()

        if verbose > 1:
            self.status['active'] = False

        return True

    def __control_thread__(self):
        self.status['active'] = True
        while self.status['active']:
            ui = input("Enter S to show status: ")
            if ui is "s" or ui is "S":
                print(self.__get_status__())
            elif ui is "q" or ui is "Q":
                self.status['active'] = False

    def __get_status__(self):
        elapsed = datetime.now() - self.status['started']
        try:
            scanned = 100 * (self.status['it_analyzed'] /
                             self.status['it_total'])
        except ZeroDivisionError:
            scanned = 0

        status_str = ("Elapsed time: {0}s. Depth {1} of {2}."
                      " Entities scanned: {3:.2f}% ({4} of {5})"
                      " Current threads running {6}").format(
                          elapsed.seconds,
                          self.status['round_curr']+1,
                          self.status['round_total'],
                          scanned,
                          self.status['it_analyzed'],
                          self.status['it_total'],
                          threading.active_count())
        return status_str

    def load_entire_dataset(self, levels,
                            where="", batch=100000, verbose=True):
        """Loads the dataset by quering to Wikidata on the desired levels

        :deprecated:
        :param int levels: Deep of the search
        :param str where: Extra where statements for SPARQL query
        :param int batch: Number of elements returned each query
        :param bool verbose: True for showing all steps the method do
        :return: True if operation was successful
        :rtype: bool
        """

        # Generate select query to get entities count
        lines = []
        for level in self.build_levels(levels):
            lines.append("?"+level[0]+" ?"+level[1]+" ?"+level[2])
        count_query = """PREFIX wikibase: <http://wikiba.se/ontology>
            SELECT (count(distinct ?object) as ?count)
            WHERE {{ ?wikidata wdt:P950 ?bne .
            {1}
            {0}
            }} """.format(" . \n".join(lines), where)
        if verbose:
            print("Query is: "+count_query)
        code, count_json = self.execute_query(count_query)
        if verbose:
            print(code, count_json)
        tuples_number = int(count_json[0]['count']['value'])

        # Generate several LIMIT & OFFSET queries
        batch = 100000
        base_query = self.build_n_levels_query(n_levels=levels)
        # Number of queries to do: add one more to last iteration
        n_queries = int(tuples_number / batch) + 1
        json_total = []

        for query in range(0, n_queries):
            if verbose:
                print("\n\nEmpieza ronda {} de {}".format(query, n_queries))
            limit_string = " LIMIT {} OFFSET {}".format(batch, 0*batch)
            # print(str(query)+"\n\n"+base_query + limit_string)
            sts, resp = self.execute_query(base_query + limit_string)
            if sts is not 200:
                print(resp)

            if verbose:
                print(sts, len(resp))
                print("Guardando en el dataset...")
            self.load_dataset_from_json(resp)
            if verbose:
                print("Guardado!")
                self.show()

    def save_to_binary(self, filepath):
        """Saves the dataset object on the disk

        The dataset will be saved with the required format for reading
        from the original library, and is prepared to be trained.

        :param str filepath: The path of the file where should be saved
        :return: True if operation was successful
        :rtype: bool
        """

        subs2 = self.train_split()
        all_dataset = {
            'entities': self.entities,
            'relations': self.relations,
            'train_subs': subs2['train_subs'],
            'valid_subs': subs2['valid_subs'],
            'test_subs': subs2['test_subs']
        }
        try:
            f = open(filepath, "wb+")
        except FileNotFoundError:
            print("The path you provided is not valid")
            return False
        pickle.dump(all_dataset, f)
        f.close()
        return True

    def load_from_binary(self, filepath):
        """Loads the dataset object from the disk

        Loads this dataset object with the binary file

        :param str filepath: The path of the binary file
        :return: True if operation was successful
        :rtype: bool
        """

        try:
            f = open(filepath, "rb")
        except FileNotFoundError:
            print("The path you provided is not valid")
            return False
        all_dataset = pickle.load(f)
        f.close()

        self.entities = all_dataset['entities']
        self.relations = all_dataset['relations']
        self.subs = all_dataset['train_subs'] + all_dataset['valid_subs'] +\
            all_dataset['test_subs']
        # self.subs = all_dataset['subs']
        return True

    def train_split(self, ratio=0.8):
        """Split subs into three lists: train, valid and test

        The triplets should have a specific name and size to be compatible
        with the original library. Splits the original triplets (self.subs) in
        three different lists: *train_subs*, *valid_subs* and *test_subs*.
        The 'ratio' param will leave that quantity for train_subs, and the
        rest will be a half for valid and the other half for test

        :param float ratio: The ratio of all triplets required for *train_subs*
        :return: A dictionary with splited subs
        :rtype: dict
        """

        data = np.matrix(self.subs)
        indices = np.arange(data.shape[0])
        np.random.shuffle(indices)
        data = data[indices]
        train_samples = int((1-ratio) * data.shape[0])

        x_train = [tuple(x) for x in data[:-train_samples]]
        x_val = [tuple(x) for x in data[-train_samples:-int(train_samples/2)]]
        x_test = [tuple(x) for x in data[-int(train_samples/2):]]

        return {"train_subs": x_train,
                "valid_subs": x_val,
                "test_subs": x_test}

    def execute_query(self, query, headers={"Accept": "application/json"}):
        """Executes a SPARQL query to the endpoint

        :param str query: The SPARQL query
        :returns: A tuple compound of (http_status, json_or_error)
        """
        # Thread limiter
        # self.query_sem.acquire()
        response = requests.get(self.WIKIDATA_ENDPOINT+query, headers=headers)
        # self.query_sem.release()
        # if response.status_code is not 200:
        #     raise Exception("Error on endpoint. HTTP status code: "+
        #                      str(response.status_code))
        if response.status_code is not 200:
            return response.status_code, response.text
        else:
            return response.status_code, response.json()["results"]["bindings"]
