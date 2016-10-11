#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# coding:utf-8
#
# Experiment class: create and train a model
# Copyright (C) 2016 Víctor Fernández Rico <vfrico@gmail.com>
# Copyright (C) 2016 Maximilian Nickel <mnick@mit.edu>
#
#   The original file can be found on
#   <https://github.com/mnick/holographic-embeddings/tree/master/kg/base.py>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function
import argparse
import numpy as np
from numpy import argsort
from collections import defaultdict as ddict
import pickle
import timeit
import logging
from sklearn.metrics import precision_recall_curve, auc, roc_auc_score

from skge import sample
from skge.util import to_tensor

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('EX-KG')
np.random.seed(137)


class Experiment(object):

    def __init__(self, dataset, th_num=0, train_all=False,
                 margin=2.0, init='nunif', lr=0.1, max_epochs=500,
                 ne=1, nbatches=100, fout=None, fin=None, test_all=50,
                 no_pairwise=False, mode='rank', sampler='random-mode', **k):
        """
        :param Dataset dataset: The dataset to train
        :param float margin: Margin for loss function
        :param string init: Initialization method
        :param float lr: Learning rate
        :param integer max_epochs: Maximum number of epochs
        :param integer ne: Number of negative examples
        :param integer nbatches: Number of batches
        :param string fout: Path to store model and results TODO->CHANGE
        :param string fin: Path to imput data TODO->CHANGE
        :param integer test_all: Evaluate the modell after x epochs
        :param bool no_pairwise: If true, trainer used is no pairwise
        :param string mode:
        :param string sampler:
        :param bool train_all: Train with all triplets or use only train subs
        """
        self.margin = margin        # Margin for loss function
        self.init = init            # Initialization method
        self.lr = lr                # Learning rate
        self.me = max_epochs        # Maximum number of iterations
        self.ne = ne                # Negative examples
        self.nb = nbatches          # Number of batches
        self.fout = fout            # Path to store model
        # self.fin = fin            # Path to imput data
        self.test_all = test_all    # Evaluate the model each x epochs
        self.no_pairwise = no_pairwise  # True if trainer is no pairwise
        self.mode = mode
        self.sampler = sampler
        self.train_all = train_all

        self.neval = -1
        self.best_valid_score = -1.0
        self.exectimes = []
        # Store the score and epochs
        self.scores = []
        self.violations = []
        self.best_epoch = None

        self.th_num = th_num
        self.dataset = dataset

    def run(self):
        """Configure ModelTrainer and start the trainer.

        :return: The trained model
        :rtype: skge.Model
        """
        if self.mode == 'rank':
            self.callback = self.ranking_callback
        elif self.mode == 'lp':
            self.callback = self.lp_callback
            self.evaluator = LinkPredictionEval
        else:
            raise ValueError('Unknown experiment mode (%s)' % self.mode)
        trainer = self.train()
        return trainer.model

    def save_trained_model(self, filepath, model):
        """Given a model and a filepath, save it to disk"""
        try:
            bin_file = open(filepath, "wb+")
        except Exception:
            print("Failed when loading file")

        return pickle.dump(bin_file, model)

    def thread_start(self, callback):
        """Used when threads are created"""
        self.run()
        callback(self)

    def ranking_callback(self, trn, with_eval=False):
        """Print basic info"""
        # print basic info
        elapsed = timeit.default_timer() - trn.epoch_start
        self.exectimes.append(elapsed)
        if self.no_pairwise:
            print("[%d][%3d] time = %ds, loss = %f" %
                  (self.th_num, trn.epoch, elapsed, trn.loss))
        else:
            print("[%d][%3d] time = %ds, violations = %d" %
                  (self.th_num, trn.epoch, elapsed, trn.nviolations))
            self.violations.append(trn.nviolations)

        if self.test_all > 0 and (trn.epoch % self.test_all == 0 or with_eval)\
                and not trn.stop_training:
            print("[%d] before eval" % self.th_num)
            pos_v, fpos_v = self.ev_valid.positions(trn.model)
            print("[%d] after eval, {} before ranking" % self.th_num)
            fmrr_valid = ranking_scores(pos_v, fpos_v, trn.epoch, 'VALID')
            print("[%d] after ranking" % self.th_num)

            print("[%d] FMRR valid = %f, best = %f" %
                  (self.th_num, fmrr_valid, self.best_valid_score))

            # Store fmrr_valid score with params.
            self.scores.append({'score': fmrr_valid,
                                'epoch': trn.epoch,
                                'type': "FMRR"})

            # If scores are too low, is better to stop the trainer
            if fmrr_valid < 0.1:
                trn.stop_training = True

            # If violations to the trainer are the same, stop the trainer
            if self.violations[0] == self.violations[-1]:
                trn.stop_training = True

            # if improved the validation error, store model and calc test error
            if fmrr_valid > self.best_valid_score:
                self.best_valid_score = fmrr_valid
                pos_t, fpos_t = self.ev_test.positions(trn.model)
                ranking_scores(pos_t, fpos_t, trn.epoch, 'TEST')

                if self.fout is not None:
                    st = {
                        'model': trn.model,
                        'pos test': pos_t,
                        'fpos test': fpos_t,
                        'pos valid': pos_v,
                        'fpos valid': fpos_v,
                        'exectimes': self.exectimes
                    }
                    with open(self.fout, 'wb') as fout:
                        pickle.dump(st, fout, protocol=2)
        return True

    def lp_callback(self, m, with_eval=False):
        # print basic info
        elapsed = timeit.default_timer() - m.epoch_start
        self.exectimes.append(elapsed)
        if self.no_pairwise:
            print("[%d][%3d] time = %ds, loss = %d" %
                  (self.th_num, m.epoch, elapsed, m.loss))
        else:
            print("[%d][%3d] time = %ds, violations = %d" %
                  (self.th_num, m.epoch, elapsed, m.nviolations))

        # if we improved the validation error, store model and calc test error
        if self.test_all > 0 and (m.epoch % self.test_all == 0 or with_eval):
            auc_valid, roc_valid = self.ev_valid.scores(m)

            print("[%d] AUC PR valid = %f, best = %f" %
                  (self.th_num, auc_valid, self.best_valid_score))

            # Store fmrr_valid score with params.
            self.scores.append({'score': auc_valid,
                                'epoch': trn.epoch,
                                'type': "AUC_PR"})
            self.scores.append({'score': roc_valid,
                                'epoch': trn.epoch,
                                'type': "AUC_ROC"})

            if auc_valid > self.best_valid_score:
                self.best_valid_score = auc_valid
                auc_test, roc_test = self.ev_test.scores(m)
                print("[%d] AUC PR test = %f, AUC ROC test = %f" %
                      (self.th_num, auc_test, roc_test))

                if self.fout is not None:
                    st = {
                        'model': m,
                        'auc pr test': auc_test,
                        'auc pr valid': auc_valid,
                        'auc roc test': roc_test,
                        'auc roc valid': roc_valid,
                        'exectimes': self.exectimes
                    }
                    with open(self.fout, 'wb') as fout:
                        pickle.dump(st, fout, protocol=2)
        return True

    def train(self):
        """Train the model"""
        # Compute training vector size
        N = len(self.dataset.entities)
        M = len(self.dataset.relations)
        sz = (N, N, M)

        # Extract triples from dataset
        subs = self.dataset.train_split()
        true_triples = subs['train_subs'] + \
            subs['test_subs'] + subs['valid_subs']

        if self.train_all:
            xs = true_triples
        else:
            xs = subs['train_subs']
        ys = np.ones(len(xs))

        # Instantiate the evaluator
        if self.mode == 'rank':
            self.ev_test = self.evaluator(subs['test_subs'], true_triples,
                                          self.neval)
            self.ev_valid = self.evaluator(subs['valid_subs'], true_triples,
                                           self.neval)
        # ¹Assuming labels are if triple is either true or false:
        elif self.mode == 'lp':
            self.ev_test = self.evaluator(subs['test_subs'],
                                          # subs['test_labels'])
                                          np.ones(len(subs['test_subs'])))
            self.ev_valid = self.evaluator(subs['valid_subs'],
                                           # subs['valid_labels'])
                                           np.ones(len(subs['valid_subs'])))

        # create sampling objects
        if self.sampler == 'corrupted':
            # create type index, here it is ok to use the whole data
            sampler = sample.CorruptedSampler(self.ne, xs, ti)
        elif self.sampler == 'random-mode':
            sampler = sample.RandomModeSampler(self.ne, [0, 1], xs, sz)
        elif self.sampler == 'lcwa':
            sampler = sample.LCWASampler(self.ne, [0, 1, 2], xs, sz)
        else:
            raise ValueError('Unknown sampler (%s)' % self.sampler)

        # Instantiate trainer
        trn = self.setup_trainer(sz, sampler)
        print("Fitting model %s with trainer %s" % (
            trn.model.__class__.__name__,
            trn.__class__.__name__)
        )
        # Start trainer
        trn.fit(xs, ys)
        self.callback(trn, with_eval=True)

        return trn


class FilteredRankingEval(object):

    def __init__(self, xs, true_triples, neval=-1):
        idx = ddict(list)
        # tt stands for true triples
        tt = ddict(lambda: {'ss': ddict(list), 'os': ddict(list)})
        self.neval = neval
        self.sz = len(xs)
        for s, o, p in xs:
            idx[p].append((s, o))

        # For each predicate (tt[p]):
        #    ss is: subjects related to object
        #    os is: objects related to subject
        for s, o, p in true_triples:
            tt[p]['os'][s].append(o)
            tt[p]['ss'][o].append(s)

        # Unpack dict
        self.idx = dict(idx)
        self.tt = dict(tt)

        self.neval = {}
        for p, sos in self.idx.items():
            if neval == -1:
                self.neval[p] = -1
            else:
                self.neval[p] = np.int(np.ceil(neval * len(sos) / len(xs)))

    def positions(self, mdl):
        pos = {}
        fpos = {}

        if hasattr(self, 'prepare_global'):
            self.prepare_global(mdl)

        for p, sos in self.idx.items():
            ppos = {'head': [], 'tail': []}
            pfpos = {'head': [], 'tail': []}

            if hasattr(self, 'prepare'):
                self.prepare(mdl, p)

            for s, o in sos[:self.neval[p]]:
                scores_o = self.scores_o(mdl, s, p).flatten()
                sortidx_o = argsort(scores_o)[::-1]
                ppos['tail'].append(np.where(sortidx_o == o)[0][0] + 1)

                rm_idx = self.tt[p]['os'][s]
                rm_idx = [i for i in rm_idx if i != o]
                scores_o[rm_idx] = -np.Inf
                sortidx_o = argsort(scores_o)[::-1]
                pfpos['tail'].append(np.where(sortidx_o == o)[0][0] + 1)

                scores_s = self.scores_s(mdl, o, p).flatten()
                sortidx_s = argsort(scores_s)[::-1]
                ppos['head'].append(np.where(sortidx_s == s)[0][0] + 1)

                rm_idx = self.tt[p]['ss'][o]
                rm_idx = [i for i in rm_idx if i != s]
                scores_s[rm_idx] = -np.Inf
                sortidx_s = argsort(scores_s)[::-1]
                pfpos['head'].append(np.where(sortidx_s == s)[0][0] + 1)
            pos[p] = ppos
            fpos[p] = pfpos

        return pos, fpos


class LinkPredictionEval(object):

    def __init__(self, xs, ys):
        ss, os, ps = list(zip(*xs))
        self.ss = list(ss)
        self.ps = list(ps)
        self.os = list(os)
        self.ys = ys

    def scores(self, mdl):
        scores = mdl._scores(self.ss, self.ps, self.os)
        pr, rc, _ = precision_recall_curve(self.ys, scores)
        roc = roc_auc_score(self.ys, scores)
        return auc(rc, pr), roc


def ranking_scores(pos, fpos, epoch, txt):
    hpos = [p for k in pos.keys() for p in pos[k]['head']]
    tpos = [p for k in pos.keys() for p in pos[k]['tail']]
    fhpos = [p for k in fpos.keys() for p in fpos[k]['head']]
    ftpos = [p for k in fpos.keys() for p in fpos[k]['tail']]
    fmrr = _print_pos(
        np.array(hpos + tpos),
        np.array(fhpos + ftpos),
        epoch, txt)
    return fmrr


def _print_pos(pos, fpos, epoch, txt):
    mrr, mean_pos, hits = compute_scores(pos)
    fmrr, fmean_pos, fhits = compute_scores(fpos)
    print(("[%3d] %s: MRR = %.2f/%.2f, "
          "Mean Rank = %.2f/%.2f, Hits@10 = %.2f/%.2f") %
          (epoch, txt, mrr, fmrr, mean_pos, fmean_pos, hits, fhits))
    return fmrr


def compute_scores(pos, hits=10):
    mrr = np.mean(1.0 / pos)
    mean_pos = np.mean(pos)
    hits = np.mean(pos <= hits).sum() * 100
    return mrr, mean_pos, hits


def cardinalities(xs, ys, sz):
    T = to_tensor(xs, ys, sz)
    c_head = []
    c_tail = []
    for Ti in T:
        sh = Ti.tocsr().sum(axis=1)
        st = Ti.tocsc().sum(axis=0)
        c_head.append(sh[np.where(sh)].mean())
        c_tail.append(st[np.where(st)].mean())

    cards = {'1-1': [], '1-N': [], 'M-1': [], 'M-N': []}
    for k in range(sz[2]):
        if c_head[k] < 1.5 and c_tail[k] < 1.5:
            cards['1-1'].append(k)
        elif c_head[k] < 1.5:
            cards['1-N'].append(k)
        elif c_tail[k] < 1.5:
            cards['M-1'].append(k)
        else:
            cards['M-N'].append(k)
    return cards
