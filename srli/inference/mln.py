import random

import srli.grounding

DEFAULT_MAX_FLIPS = 50000
DEFAULT_NOISE = 0.1

HARD_WEIGHT = 1000.0

class MLN(object):
    def __init__(self, relations, rules, weights = None, **kwargs):
        self._relations = relations
        self._rules = rules

        if (weights is not None and len(weights) > 0):
            self._weights = weights
        else:
            self._weights = [1.0] * len(self._rules)

    def solve(self, max_flips = DEFAULT_MAX_FLIPS, noise = DEFAULT_NOISE, seed = None, **kwargs):
        if (seed is None):
            seed = random.randint(0, 2**31)
        random.seed(seed)

        raw_ground_rules = srli.grounding.ground(self._relations, self._rules)
        ground_rules, atom_grounding_map = self._process_ground_rules(raw_ground_rules)

        atom_values = {}
        atom_losses = {}
        for atom_index in atom_grounding_map:
            atom_values[atom_index] = random.randint(0, 1)
            atom_losses[atom_index] = 0.0

        for flip in range(max_flips):
            # Reset
            for atom_index in atom_grounding_map:
                atom_losses[atom_index] = 0.0

            # Compute losses.
            total_loss = 0.0
            for ground_rule in ground_rules:
                loss = ground_rule.loss(atom_values)

                total_loss += loss
                for atom_index in ground_rule.atoms:
                    atom_losses[atom_index] += loss

            # Pick a random ground rule.
            ground_rule_index = random.randint(0, len(ground_rules) - 1)

            # Flip a coin.
            # On heads, flip a random atom in the ground rule.
            # On tails, flip the most dissatisfied atom in the ground rule.
            if (random.random() < noise):
                flip_atom_index = random.choice(ground_rules[ground_rule_index].atoms)
                atom_values[flip_atom_index] = 1.0 - atom_values[flip_atom_index]
            else:
                flip_atom_index = None
                for atom_index in ground_rules[ground_rule_index].atoms:
                    if (flip_atom_index is None or atom_losses[atom_index] > atom_losses[flip_atom_index]):
                        flip_atom_index = atom_index

                atom_values[flip_atom_index] = 1.0 - atom_values[flip_atom_index]

            # TEST
            print("MLN Iteration %d, Loss: %f." % (flip, total_loss))


        # TEST
        return {}

    def _process_ground_rules(self, raw_ground_rules):
        """
        Take in the raw ground rules and collapse all the observed values.
        Return a mapping of grond atoms to all involved ground rules.
        """

        atom_grounding_map = {}
        ground_rules = []

        relation_counts = []
        for relation in self._relations:
            relation_counts.append(len(relation.get_observed_data()) + len(relation.get_unobserved_data()));

        for raw_ground_rule in raw_ground_rules:
            weight = self._weights[raw_ground_rule.ruleIndex]
            if (weight is None):
                weight = HARD_WEIGHT

            atoms = []
            coefficients = []
            constant = raw_ground_rule.constant

            for i in range(len(raw_ground_rule.atoms)):
                observed, value = self._fetch_atom(relation_counts, raw_ground_rule.atoms[i])

                if (observed):
                    value *= raw_ground_rule.coefficients[i]
                    constant -= value
                else:
                    atoms.append(raw_ground_rule.atoms[i])
                    coefficients.append(raw_ground_rule.coefficients[i])

            ground_rule = GroundRule(weight, atoms, coefficients, constant, raw_ground_rule.operator)

            ground_rule_index = len(ground_rules)
            ground_rules.append(ground_rule)

            for atom_index in atoms:
                if (atom_index not in atom_grounding_map):
                    atom_grounding_map[atom_index] = []
                atom_grounding_map[atom_index].append(ground_rule_index)

        return ground_rules, atom_grounding_map

    def _fetch_atom(self, relation_counts, index):
        # Get the relation.
        for relation_index in range(len(self._relations)):
            if (index < relation_counts[relation_index]):
                break
            index -= relation_counts[relation_index]

        relation = self._relations[relation_index]

        # Check for an observed atom.
        if (index < len(relation.get_observed_data())):
            atom_data = relation.get_observed_data()[index]

            value = 1.0
            if (len(atom_data) == relation.arity() + 1):
                value = float(atom_data[-1])

            return True, value

        index -= len(relation.get_observed_data())

        # Get an unobserved atom_data.

        atom_data = relation.get_unobserved_data()[index]

        value = None
        if (len(atom_data) == relation.arity() + 1):
            value = float(atom_data[-1])

        return False, value

class GroundRule(object):
    def __init__(self, weight, atoms, coefficients, constant, operator):
        self.weight = weight
        self.atoms = atoms
        self.coefficients = coefficients
        self.constant = constant
        self.operator = operator

    def loss(self, atom_values):
        value = 0.0

        # TEST
        # assert self.operator == '|', self.operator

        for i in range(len(self.atoms)):
            truth_value = atom_values[self.atoms[i]]
            if (self.coefficients[i] < 1.0):
                truth_value = 1.0 - truth_value

            value = min(1.0, value + truth_value)

        return self.weight * (1.0 - value)
