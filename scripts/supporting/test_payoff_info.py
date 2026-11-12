"""Free checks for the released payoff cells. Run: python -m unittest scripts.supporting.test_payoff_info"""
import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.supporting import payoff_info as info
from scripts.supporting.prepare_data import MODEL_COLUMNS, prepare_analysis_data


class PayoffInfoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        csv.field_size_limit(10_000_000)
        with (info.ROOT / 'data/regression_data.csv').open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            cls.columns, cls.rows = reader.fieldnames, list(reader)
        cls.payloads = {r['observation_id']: json.loads(r[info.COLUMN]) for r in cls.rows}
        cls.records = {k: v for p in cls.payloads.values() for k, v in p['payoffs'].items()}
        cls.catalog = {p['payoff_id']: p for p in info.read_json(info.ROOT / 'data/raw_payoff_catalog.json')}

    def test_column_position_and_coverage(self):
        self.assertEqual(self.columns, ['observation_id', info.COLUMN, *MODEL_COLUMNS[1:]])
        self.assertEqual(len(self.rows), 141)
        self.assertEqual(len(self.records), 103)
        self.assertEqual(sum(r['coverage'] == 'numerical' for r in self.records.values()), 98)
        self.assertEqual(sum(p['coverage'] == 'includes_proof_only' for p in self.payloads.values()), 2)

    def test_compact_tables_round_trip_to_original_catalog(self):
        for payoff_id, record in self.records.items():
            with self.subTest(payoff_id=payoff_id):
                self.assertEqual(info.unpack_catalog(record['catalog']), self.catalog[payoff_id])
                for schedule in record['catalog'].get('schedules', {}).values():
                    for issue in schedule['issues']:
                        self.assertEqual(len(issue['options']), len(issue['payoffs']))
                        self.assertTrue(all(isinstance(row, list) for row in issue['payoffs']))

    def test_component_links_and_two_levels_of_weights(self):
        expected = pd.read_csv(info.ROOT / 'data/derived/component_evidence.csv').set_index('component_id')
        linked = []
        for observation_id, payload in self.payloads.items():
            self.assertAlmostEqual(sum(c['weight'] for c in payload['components']), 1)
            for component in payload['components']:
                linked.append(component['component_id'])
                row = expected.loc[component['component_id']]
                self.assertEqual(row.study_id, observation_id)
                self.assertEqual(row.payoff_id, component['payoff_id'])
                self.assertAlmostEqual(row.main_weight, component['weight'])
                self.assertIn(component['payoff_id'], payload['payoffs'])
        self.assertEqual(set(linked), set(expected.index))
        self.assertEqual(len(linked), len(expected))
        pooled = self.payloads['SRU0286']['payoffs']['market_alternatives_remaining_13_pooled']['catalog']
        self.assertEqual(len(pooled['components']), 13)
        self.assertEqual(len(pooled['schedules']), 1)
        self.assertAlmostEqual(sum(p['aggregation_weight'] for p in pooled['components']), 1)

    def test_cell_calculations_read_no_other_data(self):
        info.calculate_record.cache_clear()
        with (patch.object(Path, 'read_text', side_effect=AssertionError('No data-file dependency')),
              patch.object(pd, 'read_csv', side_effect=AssertionError('No CSV dependency')),
              patch.object(np, 'load', side_effect=AssertionError('No saved acceptance grid'))):
            results = {r['observation_id']: info.calculate(r[info.COLUMN]) for r in self.rows}
        differences, unavailable = set(), set()
        for row in self.rows:
            result = results[row['observation_id']]
            for name in info.MEASURES:
                if result[name] is None:
                    unavailable.add((row['observation_id'], name))
                elif not np.isclose(result[name], float(row[name]), atol=1e-12, rtol=0):
                    differences.add((row['observation_id'], name))
            self.assertAlmostEqual(result['coded_number_of_compatible_issues'],
                                   float(row['number_of_compatible_issues']))
        self.assertEqual(differences, {(i, 'number_of_compatible_issues') for i in
                                      ['SRU0114', 'SRU0349', 'SRU0350', 'SRU0351', 'SRU0359']})
        self.assertEqual(unavailable, {(i, 'number_of_compatible_issues') for i in
                                      ['SRU0108', 'NORTHCRAFT1998_STUDY1']})

    def test_actual_raw_table_changes_change_metrics(self):
        record = json.loads(info.dumps(self.records['new_recruit_r4500_r4500']))
        before = info.calculate_record(info.dumps(record))
        self.assertGreater(before['bargaining_zone_share'], 0)
        for schedule in record['catalog']['schedules'].values():
            for issue in schedule['issues']:
                issue['payoffs'] = [[0, 0] for _ in issue['payoffs']]
        after = info.calculate_record(info.dumps(record))
        self.assertEqual(after['bargaining_zone_share'], 0)
        self.assertEqual(after['search_complexity'], 1)

    def test_proof_only_records_do_not_fabricate_tables_or_compatibility(self):
        proofs = [r for r in self.records.values() if r['coverage'] == 'proof_only']
        self.assertEqual(len(proofs), 5)
        for record in proofs:
            self.assertFalse(record['catalog']['components'])
            self.assertNotIn('schedules', record['catalog'])
            result = info.calculate_record(info.dumps(record))
            self.assertIsNone(result['number_of_compatible_issues'])
            self.assertEqual(result['search_complexity'], 0)
            self.assertEqual(result['bargaining_zone_share'], 1)
            self.assertIn('source coding', result['control_basis'])

    def test_programmed_cap_does_not_become_a_seller_reservation(self):
        record = self.records['sale_cafe_buyer_cap_1550']
        model = record['catalog']['payoff_function_input']
        self.assertEqual(model['reservation_values'], [6100, None])
        self.assertEqual(record['programmed_rule']['programmed_buyer_score_cap'], 1550)
        result = info.calculate_record(info.dumps(record))
        self.assertEqual(result['bargaining_zone_share'], 0)
        self.assertTrue(any('not a seller reservation value' in text for text in result['warnings']))

    def test_unknown_pooled_allocation_requires_invariance(self):
        raw = info.unpack_catalog(self.records['beersma_de_dreu_2002_market_four_versions_pooled']['catalog'])
        self.assertTrue(any(p['aggregation_weight'] is None for p in raw['components']))
        self.assertEqual(info.table_parts(raw)['search_complexity'], 0)
        for option in raw['components'][0]['schedule']['issues'][0]['options']:
            option['payoffs'] = [-1_000_000] * len(option['payoffs'])
        with self.assertRaisesRegex(ValueError, 'Unknown within-payoff allocation'):
            info.table_parts(raw)

    def test_unbounded_minimum_keeps_source_meaning(self):
        parts = [p for entry in self.catalog.values() for p in entry['components']
                 if p.get('reservation_values') and 'unbounded' in p['reservation_values']]
        self.assertTrue(parts)
        self.assertTrue(all(isinstance(p['reservation_values'], list) for p in parts))

    def test_unsupported_function_and_changed_procedure_are_rejected(self):
        record = json.loads(info.dumps(self.records['leonardelli_soccer_exp5_owner_high']))
        record['catalog']['payoff_function_input']['payoff_formulas']['Owner'] = 'different formula'
        with self.assertRaisesRegex(ValueError, 'changed/unsupported source function'):
            info.calculate_record(info.dumps(record))
        record = json.loads(info.dumps(self.records['leonardelli_soccer_exp5_owner_high']))
        record['calculation_settings']['halton_shift_seed'] += 1
        with self.assertRaisesRegex(ValueError, 'declared released numerical procedure'):
            info.calculate_record(info.dumps(record))

    def test_bad_weights_and_missing_embedded_table_fail(self):
        payload = json.loads(info.dumps(self.payloads['SRU0286']))
        payload['components'][0]['weight'] += .1
        with self.assertRaisesRegex(ValueError, 'weights must sum to one'):
            info.calculate(payload)
        payload = json.loads(info.dumps(self.payloads['SRU0286']))
        next(iter(payload['payoffs'].values()))['catalog']['schedules'].clear()
        with self.assertRaises(KeyError):
            info.calculate(payload)

    def test_default_preparation_rebuilds_the_same_json(self):
        with TemporaryDirectory() as temporary:
            prepared = prepare_analysis_data(info.ROOT, Path(temporary))
            self.assertEqual(list(prepared['main'].columns), self.columns)
            self.assertEqual(prepared['main'].payoff_json.tolist(), [r[info.COLUMN] for r in self.rows])
            saved = pd.read_csv(Path(temporary) / 'regression_data.csv', float_precision='round_trip')
            self.assertEqual(saved.payoff_json.tolist(), prepared['main'].payoff_json.tolist())
            self.assertNotIn(info.COLUMN, prepared['strict'])
            expected = pd.read_csv(info.ROOT / 'data/regression_data.csv', float_precision='round_trip')
            np.testing.assert_array_equal(saved[MODEL_COLUMNS[1:]], expected[MODEL_COLUMNS[1:]])


if __name__ == '__main__':
    unittest.main()
