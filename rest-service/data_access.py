import os
import sqlite3
from kgeserver.dataset import Dataset
database_file = "server.db"


class MainDAO():
    def __init__(self, database_file="server.db"):
        "Comprueba si existe la base de datos y/o la inicializa"

        self.database_file = database_file

        # Create the file itself
        try:
            os.stat(self.database_file)
        except OSError:
            # File does not exist. Create
            f = open(self.database_file, "w+")
            f.close()
            self.build_basic_db()

        # Path where all binary files have its relative path
        self.bin_path = "../"

    def build_basic_db(self):
        self.execute_query("CREATE TABLE dataset "
                           "(id INTEGER UNIQUE PRIMARY KEY, "
                           "binary_dataset TEXT, "
                           "binary_model TEXT, "
                           "binary_index TEXT,"
                           "embedding_size INTEGER, status INTEGER)")

        self.execute_query("INSERT INTO dataset VALUES "
                           "(0, 'wikidata_25k.bin', '', '', NULL, 0)")

    def execute_query(self, query):
        conn = sqlite3.connect(self.database_file)
        results = []
        c = conn.cursor()
        c.execute(query)
        row = c.fetchone()
        conn.commit()
        c.close()
        return row


class DatasetDAO(MainDAO):
    def __init__(self, database_file="server.db"):
        super(DatasetDAO, self).__init__(database_file=database_file)
        self.dataset = {
            "status": None,
            "entities": None,
            "relations": None,
            "triples": None,
            "algorithm": None,
            "id": None
        }

    def get_dataset_by_id(self, dataset_id):
        query = "SELECT * FROM dataset WHERE id={0}".format(dataset_id)
        res = self.execute_query(query)
        print(res)
        dtst = Dataset()
        dtst.load_from_binary(self.bin_path+res[1])
        self.dataset['status'] = res[5]
        self.dataset['algorithm'] = res[4]
        self.dataset['triples'] = len(dtst.subs)
        self.dataset['entities'] = len(dtst.entities)
        self.dataset['relations'] = len(dtst.relations)
        self.dataset['id'] = dataset_id
        return self.dataset
