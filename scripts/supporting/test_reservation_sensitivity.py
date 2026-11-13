"""Synthetic checks for the optional numerical boundary, with no external calls."""
import unittest
import numpy as np

from .payoff_metrics import (numeric_accepts, minimum_boundary_metrics,
                             metrics_from_acceptance, metrics_from_programmed_rule, metrics_from_source_proof)
from .sampled_metrics import sampled_two_party_metrics
from .source_functions import halton
from .reservation_sensitivity import _weights


class ReservationBoundaryTests(unittest.TestCase):
    def test_numeric_equality_and_unbounded_rv(self):
        np.testing.assert_array_equal(numeric_accepts([0, 1], 0), [True, True])
        np.testing.assert_array_equal(numeric_accepts([0, 1], 0, True), [False, True])
        self.assertTrue(numeric_accepts(-100, -np.inf, True))

    def test_liu_source_boundary_not_legacy_first_accepted_grid_point(self):
        grid = np.arange(0, 2001, 5)
        # Source: 900 or lower is unacceptable. In the coded five-point grid,
        # the first accepted total is 905; 925 must not be shifted again.
        np.testing.assert_array_equal(numeric_accepts(grid, 900, True),
                                      numeric_accepts(grid, 905, False))
        self.assertFalse(numeric_accepts(900, 900, True))
        self.assertTrue(numeric_accepts(905, 900, True))
        self.assertTrue(numeric_accepts(925, 900, True))

    def test_compression_matches_weighted_complete_grid(self):
        rng = np.random.default_rng(20261112)
        for parties in (2, 3):
            for index in range(30):
                issues = [rng.integers(0, 3, size=(n, parties)).astype(float) for n in (4, 3, 4)]
                issues[0] -= 2
                reservations = sum(issue.min(axis=0) for issue in issues)
                if index % 2:
                    reservations[0] -= 1
                shape = tuple(len(issue) for issue in issues)
                coordinates = np.indices(shape).reshape(len(shape), -1)
                totals = sum(issue[coordinates[k]] for k, issue in enumerate(issues))
                quota, mandatory = (parties - 1 if index % 3 else parties), ([0] if index % 4 else [])
                brute = metrics_from_acceptance(totals > reservations, shape, quota, mandatory)
                compressed = minimum_boundary_metrics(issues, reservations, quota, mandatory)
                for key in ('search_complexity', 'bargaining_zone_share'):
                    self.assertAlmostEqual(brute[key], compressed[key], places=14)

    def test_sampled_paths_match_both_bruteforce_boundaries(self):
        issues = [np.array([[0., 2.], [1., 1.], [2., 0.], [1., 1.]]),
                  np.array([[-1., 0.], [0., -1.], [1., 1.]]),
                  np.array([[0., 0.], [1., 0.], [0., 1.]])]
        reservations, n, seed = np.array([2., 2.]), 4096, 20260827
        shape = tuple(len(issue) for issue in issues)
        coordinates = np.indices(shape).reshape(len(shape), -1)
        totals = sum(issue[coordinates[k]] for k, issue in enumerate(issues))
        starts = np.minimum((halton(n, len(shape), seed) * shape).astype(int), np.array(shape) - 1)
        indices = np.ravel_multi_index(starts.T, shape)
        for strict in (False, True):
            accepts = numeric_accepts(totals, reservations, strict)
            brute = metrics_from_acceptance(accepts, shape, 2, starting_indices=indices)
            sampled = sampled_two_party_metrics(issues, reservations, n, seed, strict)
            self.assertEqual(brute['search_complexity'], sampled['search_complexity'])
            self.assertEqual(accepts[indices].all(axis=1).mean(), sampled['bargaining_zone_share'])

    def test_programmed_classifier_and_joint_source_constraints(self):
        rule = {'shape': [4], 'buyer_score_coefficients': [1],
                'buyer_minimum': 1, 'programmed_buyer_score_cap': 2}
        self.assertEqual(metrics_from_programmed_rule(rule)['bargaining_zone_share'], .5)
        self.assertEqual(metrics_from_programmed_rule(rule, True)['bargaining_zone_share'], .25)
        for x in range(4, 45):
            weights = _weights(x)
            self.assertAlmostEqual(weights[0] + weights[1], 47 / 91)
            self.assertAlmostEqual(weights[0] + weights[2], 46 / 91)
            self.assertTrue((weights * 91 >= 2).all())
        with self.assertRaises(ValueError):
            _weights(2)

    def test_strict_source_certificate_requires_its_explicit_assumption(self):
        proof = {'kind': 'all_payoffs_meet_reservations', 'lower_payoff_bounds': [0, 0],
                 'reservation_values': [0, 0], 'source': 'Synthetic source', 'strict_boundary': {
                    'kind': 'nonnegative_unique_zero_profiles_with_congruent_escape',
                    'calculation_comparison': 'gt', 'offer_shape': [5, 5], 'zero_profiles': [1, 1],
                    'zero_profiles_disjoint': True, 'congruent_step_proof': 'Synthetic escape proof',
                    'unprinted_unique_zero_endpoints_assumed': True, 'assumption': 'Explicit synthetic assumption',
                    'source': 'Synthetic certificate'}}
        self.assertEqual(metrics_from_source_proof(proof)['bargaining_zone_share'], 1.)
        result = metrics_from_source_proof(proof, True)
        self.assertEqual(result['bargaining_zone_share'], 23 / 25)
        self.assertEqual(result['search_complexity'], 0.)
        proof['strict_boundary']['assumption'] = ''
        with self.assertRaises(ValueError):
            metrics_from_source_proof(proof, True)


if __name__ == '__main__':
    unittest.main()
