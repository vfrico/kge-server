import requests
import json
import pickle

class Dataset():
    WIKIDATA_ENDPOINT = """https://query.wikidata.org/bigdata/namespace/wdq/sparql?query="""
    entities = []
    relations = []
    subs = []
    
    def show(self):
        print("%d entities, %d relations, %d tripletas" % 
              (len(self.entities), len(self.relations), len(self.subs)))
        
        print("\nEntities:")
        for entity in self.entities:
            print(entity)
        print("\nRelations:")
        for relation in self.relations:
            print(relation)
        print("\nTripletas:")
        for sub in self.subs:
            print(sub)
        
    
    def add_element(self, element, complete_list, only_uri=False):
        if only_uri == True and type(element) is not type(""):
            #print("NO se puede añadir elemento del tipo: ", type(element))
            return
        
        try:
            #Item is on the list -> you don't need to add again
            return complete_list.index(element)
        except ValueError:
            # Item is not on the list -> add it and return id
            complete_list.append(element)
            return len(complete_list)-1
        

    def extract_entity(self,entity):
        if entity["type"] == "uri":
            return entity["value"]
        elif entity["type"] == "literal":
            return entity
        elif entity["type"] == "bnode":
            return entity

    def load_dataset_from_json(self, json, only_uri=True):
        for triplet in jsonlist:
            id_obj = self.add_element(self.extract_entity(triplet["object"]), self.entities, only_uri=only_uri)
            id_subj = self.add_element(self.extract_entity(triplet["subject"]), self.entities, only_uri=only_uri)
            id_pred = self.add_element(self.extract_entity(triplet["predicate"]), self.relations, only_uri=only_uri)

            self.subs.append([id_obj, id_subj, id_pred])
            
    def load_dataset_from_query(self, query, only_uri=False):
        headers = {"Accept" : mime_format}
        response = requests.get(WIKIDATA_ENDPOINT + query, headers=headers)
        jsonlist = response.json()["results"]["bindings"]
        
        self.load_dataset_from_json(jsonlist, only_uri=only_uri)
    
    def save_to_binary(self, filepath):
        all_dataset = {
            'entities': self.entities,
            'relations': self.relations,
            'subs': self.subs
        }
        try:
            f = open(filepath, "wb+")
        except Exception:
            print("The path you provided is not valid.")
            return False
        pickle.dump(all_dataset, f)
        f.close()
    
    def load_from_binary(self, filepath):
        try:
            f = open(filepath, "rb")
        except Exception:
            print("The path you provided is not valid.")
            return False
        all_dataset = pickle.load(f)
        f.close()
        
        self.entities = all_dataset['entities']
        self.relations = all_dataset['relations']
        self.subs = all_dataset['subs']
        
