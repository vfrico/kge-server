import os
import data_access_base
import kgeserver.dataset as dataset
from algorithm_dao import AlgorithmDAO


class DatasetDTO(data_access_base.DTOClass):
    id = None
    status = None
    entities = None
    relations = None
    triples = None
    algorithm = None

    _binary_dataset = None
    _binary_model = None
    _binary_index = None

    def from_dict(self, result_dict):
        """Given a result dict, with proper fields, builds a datasetDTO

        :param dict result_dict: A dict with all fields required
        :return: A dataset dictionary or None
        :rtype: dict
        """  # INFO:This method is intended ONLY to fill a dataset dict.
        # Query has an object
        self._binary_dataset = result_dict['binary_dataset']
        self._binary_model = result_dict['binary_model']
        self._binary_index = result_dict['binary_index']
        self.status = result_dict['status']
        self.id = int(result_dict['id'])

        if result_dict['triples'] and result_dict['relations'] and\
           result_dict['entities']:
            # These fields are filled and can be readable
            self.triples = result_dict['triples']
            self.entities = result_dict['entities']
            self.relations = result_dict['relations']
        else:
            # Fields should be readed from file
            dtst = dataset.Dataset()
            dtst.load_from_binary("../datasets/"+self._binary_dataset)
            self.triples = len(dtst.subs)
            self.entities = len(dtst.entities)
            self.relations = len(dtst.relations)

        alg_dao = AlgorithmDAO()
        algorithm, err = alg_dao.get_algorithm_by_id(result_dict['algorithm'])
        if algorithm is None:
            raise LookupError(err)
        self.algorithm = algorithm

        return None

    def is_untrained(self):
        """Check if dataset is in untrained state

        Should return True if status is 0 or 1

        :return: True if dataset is in untrained state
        :rtype: boolean
        """
        if self.status is None:
            return None
        elif self.status < 2 and self.status >= 0:
            return True
        else:
            return False

    def is_trained(self):
        """Check if dataset is in untrained state

        Should return True if status is 1

        :return: True if dataset is in untrained state
        :rtype: boolean
        """
        if self.status is None:
            return None
        elif self.status >= 1:
            return True
        else:
            return False

    def get_binary_index(self):
        return os.path.join("../datasets/", self._binary_index)

    def get_binary_dataset(self):
        return os.path.join("../datasets/", self._binary_dataset)

    def get_binary_model(self):
        return os.path.join("../datasets/", self._binary_model)
