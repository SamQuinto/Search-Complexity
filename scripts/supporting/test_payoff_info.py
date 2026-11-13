"""Free checks for the released payoff cells. Run: python -m unittest scripts.supporting.test_payoff_info"""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.supporting import payoff_info as info
from scripts.supporting.prepare_data import MODEL_COLUMNS, build_data, prepare_analysis_data


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
        outcomes = pd.read_csv(info.ROOT / 'data/sources/study_outcomes.csv')
        decisions = pd.read_csv(info.ROOT / 'data/component_decisions.csv', keep_default_na=False)
        included = set(decisions.loc[decisions.main_included.eq('Y'), 'component_id'])
        expected = set(outcomes.loc[outcomes.component_id.isin(included), 'study_id'])
        self.assertEqual(set(self.payloads), expected)
        self.assertEqual(set(self.records), set(self.catalog))
        for payload in self.payloads.values():
            self.assertEqual(payload['calculation_rule']['numeric_RV_comparison'], '>')
            for record in payload['payoffs'].values():
                self.assertEqual(record['calculation_rule'], payload['calculation_rule'])
                self.assertIn(record['coverage'], ('numerical', 'proof_only'))

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
        self.assertEqual(differences, set())
        self.assertEqual(unavailable, set())

    def test_actual_raw_table_changes_change_metrics(self):
        record = json.loads(info.dumps(self.records['new_recruit_r4500_r4500']))
        before = info.calculate_record(info.dumps(record))
        self.assertGreater(before['bargaining_zone_share'], 0)
        for schedule in record['catalog']['schedules'].values():
            for issue in schedule['issues']:
                issue['payoffs'] = [[v - 1_000_000 for v in row] for row in issue['payoffs']]
        after = info.calculate_record(info.dumps(record))
        self.assertEqual(after['bargaining_zone_share'], 0)
        self.assertEqual(after['search_complexity'], 1)

    def test_proof_records_use_directly_reported_controls_with_source_pages(self):
        proofs = [r for r in self.records.values() if r['coverage'] == 'proof_only']
        for record in proofs:
            self.assertFalse(record['catalog']['components'])
            self.assertNotIn('schedules', record['catalog'])
            result = info.calculate_record(info.dumps(record))
            self.assertEqual(result['number_of_compatible_issues'],
                             record['proof']['source_verified_controls']['compatible'])
            self.assertEqual(result['search_complexity'], 0)
            if record['catalog']['payoff_id'].startswith('northcraft_1998_employment_'):
                self.assertEqual(result['bargaining_zone_share'], .999872)
                self.assertEqual(info.calculate_record(info.dumps(record), strict=False)['bargaining_zone_share'], 1)
            else:
                self.assertEqual(result['bargaining_zone_share'], 1)
            self.assertIn('Directly reported source controls', result['control_basis'])
            self.assertIn('PDF p.', record['proof']['controls_source'])

    def test_physical_option_alignment(self):
        fresh = info.input_records(info.ROOT)
        kern = info.unpack_catalog(fresh['player7_kern']['catalog'])
        first = kern['components'][0]['schedule']['issues'][0]
        self.assertEqual(first['name'], 'Male Lead')
        self.assertEqual(first['options'][0]['option'], 'Tom Cruise')
        self.assertEqual(first['options'][0]['payoffs'], [2200,100])
        self.assertEqual(first['options'][-1], {'option':'Bruce Willis', 'payoffs':[400,1250]})
        self.assertEqual(info.record_controls(fresh['player7_kern'])['number_of_compatible_issues'], 1)
        murnighan = info.unpack_catalog(fresh['murnighan_1999_development_pooled']['catalog'])
        for part in murnighan['components']:
            retail, inspector = part['schedule']['issues'][1], part['schedule']['issues'][4]
            self.assertEqual(retail['options'][0], {'option': '12000 ft', 'payoffs': [2400.0,2400.0]})
            self.assertEqual(inspector['options'][0], {'option': 'Mayer', 'payoffs': [600.0,600.0]})
        self.assertEqual(info.record_controls(fresh['murnighan_1999_development_pooled'])['number_of_compatible_issues'], 2)

    def test_control_mismatch_blocks_input_loading_and_attachment(self):
        with TemporaryDirectory() as temporary:
            copied = Path(temporary)
            for name in ['raw_payoff_catalog.json', 'acceptability_proofs.json',
                         'programmed_acceptance_rules.json', 'approval_rules.csv', 'within_payoff_weights.csv',
                         'sources/structure_inputs.csv', 'sources/study_outcomes.csv']:
                target = copied / 'data' / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(info.ROOT / 'data' / name, target)
            shutil.copytree(info.ROOT / 'data/payoff_schedules', copied / 'data/payoff_schedules')
            path = copied / 'data/sources/structure_inputs.csv'
            frame = pd.read_csv(path)
            frame.loc[frame.payoff_id.eq('player7_kern'), 'number_of_compatible_issues'] = 7
            frame.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, 'number_of_compatible_issues.*disagrees'):
                info.input_records(copied)
            with self.assertRaisesRegex(ValueError, 'number_of_compatible_issues.*disagrees'):
                info.attach_payoff_info(pd.DataFrame(self.rows), copied, pd.DataFrame())
            with self.assertRaisesRegex(ValueError, 'number_of_compatible_issues.*disagrees'):
                build_data(copied, copied / 'rebuilt')

    def test_proof_control_mismatch_is_an_error(self):
        record = info.input_records(info.ROOT)['northcraft_1998_employment_linear_r0_r0']
        record['proof']['source_verified_controls']['compatible'] = 0
        with self.assertRaisesRegex(ValueError, 'number_of_compatible_issues.*disagrees'):
            info.calculate_record(info.dumps(record))

    def test_northcraft_partial_tables_keep_omitted_arrays_null(self):
        fresh = info.input_records(info.ROOT)
        for variant in ['decreasing', 'linear', 'increasing']:
            record = fresh[f'northcraft_1998_employment_{variant}_r0_r0']
            partial = record['catalog']['partial_source_tables']
            self.assertEqual(len(partial['printed_templates']), 4)
            self.assertIsNone(partial['unprinted_integrative_issues']['numerical_payoffs'])
            self.assertEqual(record['coverage'], 'proof_only')

    def test_martin_raugh_is_excluded_but_original_outcomes_are_retained(self):
        ids = {'martin_raugh_2020_fundraiser', 'martin_raugh_2020_robot'}
        self.assertTrue(ids.isdisjoint(info.input_records(info.ROOT)))
        self.assertNotIn('SRU0108', self.payloads)
        decisions = pd.read_csv(info.ROOT / 'data/component_decisions.csv')
        excluded = decisions.loc[decisions.payoff_id.isin(ids)]
        self.assertEqual(len(excluded), 2)
        self.assertTrue(excluded.main_included.eq('N').all())
        self.assertTrue(excluded.strict_included.eq('N').all())
        structures = pd.read_csv(info.ROOT / 'data/sources/structure_inputs.csv')
        self.assertTrue(structures.loc[structures.payoff_id.isin(ids), 'main_eligible'].eq(False).all())
        self.assertTrue(ids.isdisjoint(pd.read_csv(info.ROOT / 'data/sources/structural_scores.csv').payoff_id))
        self.assertTrue(ids.isdisjoint(p['payoff_id'] for p in info.read_json(info.ROOT / 'data/acceptability_proofs.json')))
        outcomes = pd.read_csv(info.ROOT / 'data/sources/study_outcomes.csv')
        self.assertEqual(set(outcomes.loc[outcomes.payoff_id.isin(ids), 'payoff_id']), ids)
        quarantine = info.read_json(info.ROOT / 'data/inventory/excluded_payoff_records.json')
        specific = [p for p in quarantine if p['payoff_id'] in ids]
        self.assertEqual({p['payoff_id'] for p in specific}, ids)
        self.assertTrue(all(p.get('exclusion_evidence') and p.get('withdrawn_acceptability_proof') for p in specific))

    def test_formal_offer_legality_cannot_establish_bargaining_zone(self):
        quarantine = info.read_json(info.ROOT / 'data/inventory/excluded_payoff_records.json')
        for record in quarantine:
            certificate = record.get('withdrawn_acceptability_proof')
            if certificate is None or certificate.get('kind') != 'all_complete_offers_allowed':
                continue
            with self.assertRaisesRegex(ValueError, 'formal offer legality'):
                info.metrics_from_source_proof(certificate)

    def test_cli_check_fails_on_any_control_difference(self):
        row = next(r.copy() for r in self.rows if r['observation_id'] == 'SRU0286')
        row['number_of_compatible_issues'] = str(float(row['number_of_compatible_issues']) + 1)
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / 'changed.csv'
            with path.open('w', encoding='utf-8', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=self.columns)
                writer.writeheader()
                writer.writerow(row)
            result = subprocess.run([sys.executable, str(info.ROOT / 'scripts/supporting/payoff_info.py'),
                                     '--csv', str(path), '--check'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

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
        self.assertTrue(all(p['aggregation_weight'] is not None for p in raw['components']))
        # Clear the explicitly assumed point weights on a separate copy. The
        # actual joint cell counts remain unknown, so strict noninvariance
        # cannot be resolved by treating the mean weights as observed counts.
        for part in raw['components']:
            part['aggregation_weight'] = None
        self.assertEqual(info.table_parts(raw, strict=False)['search_complexity'], 0)
        with self.assertRaisesRegex(ValueError, 'Unknown within-payoff allocation'):
            info.table_parts(raw, strict=True)

    def test_unbounded_minimum_keeps_source_meaning(self):
        parts = [p for entry in self.catalog.values() for p in entry['components']
                 if p.get('reservation_values') and 'unbounded' in p['reservation_values']]
        self.assertTrue(all(isinstance(p['reservation_values'], list) for p in parts))

    def test_liu_source_boundary_uses_actual_coded_grid(self):
        key = 'liu_2019_allred_employment_r925_r925'
        if key not in self.catalog:
            self.skipTest('Liu is not an active source record.')
        raw = info.unpack_catalog(self.records[key]['catalog'])
        self.assertEqual(raw['components'][0]['reservation_values'], [900, 900])
        boundary = raw['source_acceptance_boundary']
        self.assertEqual(boundary['comparison'], 'gt')
        first_allowed = json.loads(json.dumps(raw))
        # The coded Allred proxy has five-point total increments: 905 is the
        # first permitted total, while 925 was a historical coding threshold.
        first_allowed['components'][0]['reservation_values'] = [905, 905]
        primary = info.table_parts(raw, strict=True)
        exact_grid_encoding = info.table_parts(first_allowed, strict=False)
        for name in ('search_complexity', 'bargaining_zone_share'):
            self.assertEqual(primary[name], exact_grid_encoding[name])

    def test_gunia_unknown_power_order_mix_is_invariant_under_both_rules(self):
        key = 'gunia_2013_new_recruit_two_power_orders_pooled'
        if key not in self.catalog:
            self.skipTest('Gunia Study 4 is not an active source record.')
        raw = info.unpack_catalog(self.records[key]['catalog'])
        self.assertTrue(all(part['aggregation_weight'] is None for part in raw['components']))
        for strict in (False, True):
            values = [info.table_parts({'components': [part]}, strict=strict) for part in raw['components']]
            pooled = info.table_parts(raw, strict=strict)
            for name in ('search_complexity', 'bargaining_zone_share'):
                for value in values:
                    self.assertAlmostEqual(value[name], pooled[name], places=12)

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
