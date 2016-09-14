import requests
import json
import pickle
import numpy as np
from queries import Queries

class Dataset():
    WIKIDATA_ENDPOINT = """https://query.wikidata.org/bigdata/namespace/wdq/sparql?query="""
    entities = []
    entities_dict = {}
    relations = []
    relations_dict = {}
    subs = []

    def show(self, verbose=False):
        "Show all elements of the dataset "
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


    def add_element(self, element, complete_list, complete_list_dict, only_uri=False):
        "Add element to a list of the dataset."

        # An URI is a string type
        if only_uri is True and type(element) is not type(""):
            return False
        elif element is False:
            return False

        try:
            # Item is on the list, return same id
            return complete_list_dict[element]

        except (KeyError,ValueError):
            # Item is not on the list, append and return id
            complete_list.append(element)
            id_item = len(complete_list)-1
            complete_list_dict[element] = id_item
            return id_item


    def extract_entity(self, entity, filters={'wdt-entity':True,'wdt-reference':False,'wdt-statement':True,'wdt-prop':True,'literal':False,'bnode':False}):
        "Check the type of the entity and returns an URI or entity item"
        if entity["type"] == "uri":
            # Not all 'uri' values are valid entities
            uri = entity["value"].split('/')
            if uri[2] == 'www.wikidata.org' and (uri[3] == "reference" and filters['wdt-reference']):
                return entity["value"]
            elif uri[2] == 'www.wikidata.org' and (uri[4] == "statement" and filters['wdt-statement']):
                return entity["value"]
            elif uri[2] == 'www.wikidata.org' and (uri[3] == "entity" and filters['wdt-entity']):
                return entity["value"]
            elif uri[2] == 'www.wikidata.org' and (uri[3] == "prop" and filters['wdt-prop']):
                return entity["value"]
            elif uri[2] == 'www.wikidata.org':
                return False
            else:
                return entity["value"]

        elif entity["type"] == "literal" and filters['literal']:
            return entity
        elif entity["type"] == "bnode" and filters['literal']:
            return entity
        else:
            return False

    def load_dataset_from_json(self, json, only_uri=False):
        "Receives a dict with three components ('object', 'subject' and 'predicate') and loads it into the dataset object"
        for triplet in json:
            id_obj = self.add_element(self.extract_entity(triplet["object"]), self.entities, self.entities_dict, only_uri=only_uri)
            id_subj = self.add_element(self.extract_entity(triplet["subject"]), self.entities, self.entities_dict, only_uri=only_uri)
            id_pred = self.add_element(self.extract_entity(triplet["predicate"]), self.relations, self.relations_dict, only_uri=only_uri)

            if id_obj is False or id_subj is False or id_pred is False:
                continue
            else:
                self.subs.append((id_obj, id_subj, id_pred))

    def load_dataset_from_query(self, query, only_uri=False):
        "Receives a Sparql query and fills dataset object with the response"
        # headers = {"Accept" : "application/json"}
        # response = requests.get(self.WIKIDATA_ENDPOINT + query, headers=headers)
        result_query = self.execute_query(query)
        if result_query[0] is not 200:
            raise Exception("Error on endpoint. HTTP status code: "+str(response.status_code))
        else:
            jsonlist = result_query[1]
        # print(json.dumps(jsonlist, indent=4, sort_keys=True))
        self.load_dataset_from_json(jsonlist, only_uri=only_uri)

    def load_dataset_from_nlevels(self, nlevels, extra_params="", only_uri=False):
        "Builds a nlevels query, executes, and loads data on object"
        query = self.build_n_levels_query(nlevels)+" "+extra_params
        print(query)
        return self.load_dataset_from_query(query, only_uri=only_uri)

    def build_levels(self, n_levels):
        "This function generates a list, needed on `build_n_levels_query`"
        ob1 = "wikidata"
        pre = "predicate"
        ob2 = "object"
        pre_base = pre
        obj_base = ob2
        predicateCount = 1
        objectCount = 1

        tripletas = []

        for level in range(1,n_levels+1):
            tripletas.append((ob1, pre, ob2))
            objectCount += 1
            predicateCount += 1
            ob1 = ob2
            ob2 = obj_base + str(objectCount)
            pre = pre_base + str(predicateCount)

        return tripletas

    def build_n_levels_query(self, n_levels=3):
        "Given a number of levels, build a sparql query"
        lines = []
        for level in self.build_levels(n_levels):
            lines.append("?"+level[0]+" ?"+level[1]+" ?"+level[2])

        query = """PREFIX wikibase: <http://wikiba.se/ontology>
construct {{ {0} }}
WHERE {{ ?wikidata wdt:P950 ?bne .
{1}
}} """.format(" . ".join(lines), " . \n".join(lines))

        return query

    def load_entire_dataset(self, levels, where="", batch=100000, verbose=True):
        """This method loads the dataset by quering desired levels to Wikidata"""
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
            #print(str(query)+"\n\n"+base_query + limit_string)
            sts, resp = self.execute_query(base_query + limit_string)
            if sts is not 200:
                print (resp)

            if verbose:
                print(sts, len(resp))
                print("Guardando en el dataset...")
            self.load_dataset_from_json(resp)
            if verbose:
                print("Guardado!")
                self.show()


    def save_to_binary(self, filepath):
        "Saves the dataset object on the disk"
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
        "Loads the dataset object from the disk"
        try:
            f = open(filepath, "rb")
        except FileNotFoundError:
            print("The path you provided is not valid")
            return False
        all_dataset = pickle.load(f)
        f.close()

        self.entities = all_dataset['entities']
        self.relations = all_dataset['relations']
        self.subs = all_dataset['train_subs'] + all_dataset['valid_subs'] + all_dataset['test_subs']
        # self.subs = all_dataset['subs']
        return True

    def train_split(self, ratio=0.8):
        "Split subs into three lists: train, valid and test"
        data = np.matrix(self.subs)
        indices = np.arange(data.shape[0])
        np.random.shuffle(indices)
        data = data[indices]
        train_samples = int((1-ratio) * data.shape[0])

        x_train = [tuple(x) for x in data[:-train_samples]]
        x_val = [tuple(x) for x in data[-train_samples:-int(train_samples/2)]]
        x_test = [tuple(x) for x in data[-int(train_samples/2):]]

        return {"train_subs":x_train, "valid_subs":x_val, "test_subs":x_test}

    def execute_query(self, query, headers={"Accept" : "application/json"}):
        "Returns a tuple of status code and json generated"
        response = requests.get(self.WIKIDATA_ENDPOINT + query, headers=headers)
        # if response.status_code is not 200:
        #     raise Exception("Error on endpoint. HTTP status code: "+str(response.status_code))
        if response.status_code is not 200:
            return response.status_code, response.text
        else:
            return response.status_code, response.json()["results"]["bindings"]
