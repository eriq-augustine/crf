#!/usr/bin/env python3

import os

import sklearn.metrics

import srli.inference
import srli.relation

import tests.data.base

THIS_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(THIS_DIR, 'data')

class SmokersModel(tests.data.base.TestModel):
    def __init__(self):
        super().__init__(DATA_DIR)

    def run(self, engine_type = srli.inference.PSL):
        friends = srli.relation.Relation('Friends', variable_types = ['Person', 'Person'])
        smokes = srli.relation.Relation('Smokes', variable_types = ['Person'])
        cancer = srli.relation.Relation('Cancer', variable_types = ['Person'])

        self.load_data(friends, observed = ['friends_obs.txt'])
        self.load_data(smokes, observed = ['smokes_obs.txt'], unobserved = ['smokes_targets.txt'], truth = ['smokes_truth.txt'])
        self.load_data(cancer, unobserved = ['cancer_targets.txt'], truth = ['cancer_truth.txt'])

        rules = [
            'Smokes(X) -> Cancer(X)',
            'Friends(A1, A2) & Smokes(A1) -> Smokes(A2)',
            'Friends(A1, A2) & Smokes(A2) -> Smokes(A1)',
            '!Smokes(X)',
        ]

        weights = [0.5, 0.4, 0.4, 0.1]
        squared = [True, True, True, True]

        engine = engine_type(
                relations = [friends, smokes, cancer],
                rules = rules,
                # PSL-specific.
                weights = weights,
                squared = squared)

        results = engine.solve()

        eval_data = self.get_eval_data(results, discretize = True)
        smokes_f1 = sklearn.metrics.f1_score(eval_data[smokes]['expected'], eval_data[smokes]['predicted'])
        cancer_f1 = sklearn.metrics.f1_score(eval_data[cancer]['expected'], eval_data[cancer]['predicted'])

        return results, {smokes: {'f1': smokes_f1}, cancer: {'f1': cancer_f1}}

    def expected_results(self):
        return {
            'Smokes': {
                'size': 4,
            },
            'Cancer': {
                'size': 6,
            }
        }

if (__name__ == '__main__'):
    model = SmokersModel()
    model.run()
