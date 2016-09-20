import numpy as np
import dataset
from skge import HolE, StochasticTrainer


class Model():

    def __init__(self, dataset):
        """
        Instanciate the model, given a Dataset. This will start the
        model, and all attributes needed from the dataset.
        """

        all_triplets = dataset.train_split()
        self.dataset = {
            #'original': dataset,
            'n_ent': len(dataset.entities),
            'n_rel': len(dataset.relations),
            'train_triplets': all_triplets['train_subs'],
            'valid_triplets': all_triplets['valid_subs'],
            'test_triplets': all_triplets['test_subs']
        }
        size = (self.dataset['n_ent'],
                self.dataset['n_ent'],
                self.dataset['n_rel'])

    def train(self, samples=50):
        N = len(self.dataset.entities)
        M = len(self.dataset.relations)
        sz = (N, N, M)

        # Get only train_subs
        xs = self.dataset.subs
        ys = np.ones(len(xs))

        model = HolE((N, N, M), samples)

        trainer = StochasticTrainer(model)
        trainer.fit(xs, ys)

        return model
