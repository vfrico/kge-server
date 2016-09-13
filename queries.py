import requests
import json


class Queries():
    def __init__(self):
        self.WD_ENDPOINT = "https://query.wikidata.org/bigdata/namespace/wdq/sparql?query="
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


    def batch_offset_json(self, query, limit, offset):
        "Return a JSON of a slice from a big query"
        query1 = query+" LIMIT {0} OFFSET {1}".format(limit, offset)

        headers = {"Accept" : "application/json"}
        response = requests.get(self.WD_ENDPOINT + query1, headers=headers)
        if response.status_code is not 200:
            return False, "Error occurred on http request. Code"+str(response.status_code)
        json_data = response.json()['results']['bindings']
        return True,json_data

    def big_query(self, n_levels=3, n_rounds=30, total=1000000):
        "Returns a JSON of a big query. **WARNING**: **MEMORY EATER**"

        query = self.build_n_levels_query(n_levels=n_levels)
        # Suponiendo un número total de líneas de 1M
        limit = int(total/n_rounds)
        offset = 0
        all_json = []
        for n_round in range(0, n_rounds):
            print("R{}: Offset: {}, limit: {}".format(n_round, offset, limit))
            status, json1 = self.batch_offset_json(query, limit, offset)
            if status:
                all_json = all_json + json1
                offset += limit
            else:
                print("Server has stated an error: {}. Exiting.".format(json1))
                break
        return all_json


    def entidades_comun_bne_json(self, where="", batch=10000):
        # Primero obtenemos el número de entidades totales:
        query = """PREFIX wikibase: <http://wikiba.se/ontology>
SELECT (count(distinct ?wikidata) as ?count)
WHERE {{
?wikidata wdt:P950 ?bne .
{0}
}} """.format(where)
        query1 = """PREFIX wikibase: <http://wikiba.se/ontology>
SELECT ?wikidata ?bne
WHERE {{
?wikidata wdt:P950 ?bne .
{0}
}} LIMIT {1} OFFSET {2}""" #format(where, limit, offset)

        headers = {"Accept" : "application/json"}
        response = requests.get(self.WD_ENDPOINT + query, headers=headers)
        if response.status_code is not 200:
            return False, "Error occurred on http request. Code"+str(response.status_code)
        json_data = response.json()['results']['bindings']
        total_number = int(json_data[0]['count']['value'])

        # Hacer sucesivas requests para obtener el total de elementos
        total_json = []
        limit = batch
        repeats = int(total_number/batch)+1
        offset = 0
        for i in range(0, repeats):
            if total_number > batch:
                limit = batch
            else:
                limit = total_number

            response = requests.get(self.WD_ENDPOINT + query1.format(where, limit, offset), headers=headers)
            if response.status_code is not 200:
                return False, "Error occurred on http request. Code"+str(response.status_code)
            json_data = response.json()['results']['bindings']
            total_json = total_json + json_data
            offset += limit
            total_number -= limit
        return True, total_json

    def get_entidades_comun_bne(self, where="", batch=10000):
        key, value = ("wikidata", "bne")
        status, json_data = self.entidades_comun_bne_json(where=where, batch=batch)
        return [(item[key]['value'], item[value]['value']) for item in json_data]
