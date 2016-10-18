import os
import sqlite3
import kgeserver.server as server
import kgeserver.dataset as dataset
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
                           "(0, 'wikidata_25k.bin', '', "
                           "'wikidata_25k.annoy.bin', 100, 2)")

        self.execute_query("INSERT INTO dataset VALUES "
                           "(1, '4levels.bin', 'modelo_guardado.bin', "
                           "'annoy_index_big.bin', 100, 2)")

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
        self.binary_dataset = None
        self.binary_model = None
        self.binary_index = None
        self.embedding_size = None

    def get_dataset_by_id(self, dataset_id):
        query = "SELECT * FROM dataset WHERE id={0}".format(dataset_id)
        res = self.execute_query(query)
        # Query has return nothing
        if res is None:
            return None, (404, "Dataset {} not found".format(dataset_id))
        # Query has an object
        self.binary_dataset = res[1]
        self.binary_model = res[2]
        self.binary_index = res[3]
        self.embedding_size = res[4]
        dtst = dataset.Dataset()
        dtst.load_from_binary(self.bin_path+self.binary_dataset)
        self.dataset['status'] = res[5]
        self.dataset['algorithm'] = res[4]
        self.dataset['triples'] = len(dtst.subs)
        self.dataset['entities'] = len(dtst.entities)
        self.dataset['relations'] = len(dtst.relations)
        self.dataset['id'] = int(dataset_id)
        return (self.dataset, dtst)

    def get_search_index(self):
        if self.dataset['status'] < 2:
            return None, (409, "Dataset {id} has {status} status and is not "
                               "ready for search".format(**self.dataset))
        search_index = server.SearchIndex()
        search_index.load_from_file(self.bin_path + self.binary_index,
                                    self.embedding_size)
        return search_index, None

    def get_server(self):
        search_index, err = self.get_search_index()
        if search_index is None:
            return None, err
        else:
            return server.Server(search_index), None
