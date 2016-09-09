import requests
import json
import pickle

    
class Dataset():
    WIKIDATA_ENDPOINT = """https://query.wikidata.org/bigdata/namespace/wdq/sparql?query="""
    entities = []
    relations = []
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
        
    
    def add_element(self, element, complete_list, only_uri=False):
        "Add element to a list of the dataset."
        if only_uri is True and type(element) is not type(""):
            return False
        elif element is False:
            return False
        
        try:
            # Item is on the list, return same id
            return complete_list.index(element)
        except ValueError:
            # Item is not on the list, append and return id
            complete_list.append(element)
            return len(complete_list)-1
        

    def extract_entity(self,entity):
        "Check the type of the entity and returns an URI or entity item"
        if entity["type"] == "uri":
            # Not all 'uri' values are valid entities
            uri = entity["value"].split('/')
            
            if uri[2] == 'www.wikidata.org' and (uri[3] == "reference" or uri[4] == "statement"):
                return False
            else:
                return entity["value"]
            
        elif entity["type"] == "literal":
            return entity
        elif entity["type"] == "bnode":
            return entity

    def load_dataset_from_json(self, json, only_uri=False):
        "Receives a dict with three components ('object', 'subject' and 'predicate') and loads it into the dataset object"
        for triplet in json:
            id_obj = self.add_element(self.extract_entity(triplet["object"]), self.entities, only_uri=only_uri)
            id_subj = self.add_element(self.extract_entity(triplet["subject"]), self.entities, only_uri=only_uri)
            id_pred = self.add_element(self.extract_entity(triplet["predicate"]), self.relations, only_uri=only_uri)

            if id_obj is False or id_subj is False or id_pred is False:
                continue
            else:
                self.subs.append([id_obj, id_subj, id_pred])
            
    def load_dataset_from_query(self, query, only_uri=False):
        "Receives a Sparql query and fills dataset object with the response"
        headers = {"Accept" : "application/json"}
        response = requests.get(self.WIKIDATA_ENDPOINT + query, headers=headers)
        jsonlist = response.json()["results"]["bindings"]
        
        self.load_dataset_from_json(jsonlist, only_uri=only_uri)
    
    def save_to_binary(self, filepath):
        "Saves the dataset object on the disk"
        all_dataset = {
            'entities': self.entities,
            'relations': self.relations,
            'subs': self.subs
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
        self.subs = all_dataset['subs']
        return True
    
    
        