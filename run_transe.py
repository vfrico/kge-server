#!/usr/bin/env python

import numpy as np
from experiment import Experiment, FilteredRankingEval
from skge import TransE, PairwiseStochasticTrainer
import dataset

class TransEEval(FilteredRankingEval):

    def prepare(self, mdl, p):
        self.ER = mdl.E + mdl.R[p]

    def scores_o(self, mdl, s, p):
        return -np.sum(np.abs(self.ER[s] - mdl.E), axis=1)

    def scores_s(self, mdl, o, p):
        return -np.sum(np.abs(self.ER - mdl.E[o]), axis=1)


class ExpTransE(Experiment):

    def __init__(self, dataset, margin=2.0, init='nunif', lr=0.1, max_epochs=500, ne=1,
                 nbatches=100, fout=None, fin=None, test_all=50,
                 no_pairwise=False, mode='rank', sampler='random-mode', ncomp=50):
        super(ExpTransE, self).__init__(dataset, margin=margin, init=init,
            lr=lr, max_epochs=max_epochs, ne=ne, nbatches=nbatches,
            fout=fout, fin=fin, test_all=test_all,
            no_pairwise=no_pairwise, mode=mode, sampler=sampler)
        self.ncomp = ncomp
        self.evaluator = TransEEval

    def setup_trainer(self, sz, sampler):
        model = TransE(sz, self.ncomp, init=self.init)
        trainer = PairwiseStochasticTrainer(
            model,
            nbatches=self.nb,
            margin=self.margin,
            max_epochs=self.me,
            learning_rate=self.lr,
            samplef=sampler.sample,
            post_epoch=[self.callback]
        )
        return trainer

if __name__ == '__main__':

    dataset = dataset.Dataset()
    dataset.load_from_binary("holographic-embeddings/data/wn18.bin")

    exp = ExpTransE(dataset, test_all=-1, max_epochs=4)
    model = exp.run()
    print(model.E)
