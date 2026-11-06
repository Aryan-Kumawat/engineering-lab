import csv
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from core import calibrate, fit_registration, fit_tcp, read_csv, save_report
from demo import generate, rotation


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def test_tcp_exact_known_truth(self):
        truth = generate(self.path, noise_mm=0)
        report = calibrate(self.path/'tcp.csv')
        np.testing.assert_allclose(report['model']['tool_offset_mm'], truth['tool_offset_mm'], atol=1e-9)
        np.testing.assert_allclose(report['model']['pivot_base_mm'], truth['pivot_base_mm'], atol=1e-9)
        self.assertLess(report['held_out']['rms_mm'], 1e-9)

    def test_registration_exact_transform(self):
        truth = generate(self.path, noise_mm=0)
        report = calibrate(self.path/'registration.csv', 'registration')
        np.testing.assert_allclose(report['model']['rotation_source_to_target'], truth['rotation_source_to_target'], atol=1e-10)
        np.testing.assert_allclose(report['model']['translation_mm'], truth['translation_mm'], atol=1e-9)

    def test_noisy_measurements_and_report_roundtrip(self):
        truth = generate(self.path)
        for mode in ['tcp','registration']:
            report = calibrate(self.path/(mode+'.csv'), mode)
            self.assertEqual(report['fit']['count'], 24)
            self.assertEqual(report['held_out']['count'], 6)
            self.assertLess(report['held_out']['rms_mm'], 0.2)
            save_report(report, self.path/mode)
            self.assertEqual(json.loads((self.path/mode/'report.json').read_text()), report)
        report = calibrate(self.path/'tcp.csv')
        np.testing.assert_allclose(report['model']['tool_offset_mm'], truth['tool_offset_mm'], atol=0.1)

    def test_held_out_measurement_never_changes_fit(self):
        generate(self.path)
        before = calibrate(self.path/'tcp.csv')
        with (self.path/'tcp.csv').open(newline='') as file:
            rows = list(csv.reader(file))
        rows[1][-1] = str(float(rows[1][-1])+10)  # Data row zero is held out.
        with (self.path/'tcp.csv').open('w',newline='') as file:
            csv.writer(file).writerows(rows)
        after = calibrate(self.path/'tcp.csv')
        self.assertEqual(before['model'], after['model'])
        self.assertGreater(after['held_out']['max_mm'], 9)
        self.assertTrue(after['warnings'])

    def test_unobservable_tcp_rejected(self):
        r = np.repeat(np.eye(3)[None,:,:], 8, axis=0)
        with self.assertRaisesRegex(ValueError,'Unobservable'):
            fit_tcp(r, np.zeros((8,3)))

    def test_reflections_and_invalid_rotations_rejected(self):
        for matrix in [np.diag([-1.,1,1]), np.eye(3)*2]:
            with self.assertRaises(ValueError):
                fit_tcp(np.repeat(matrix[None,:,:],8,axis=0), np.zeros((8,3)))

    def test_collinear_points_rejected(self):
        points = np.array([[0.,0,0],[1,0,0],[2,0,0]])
        with self.assertRaisesRegex(ValueError,'collinear'):
            fit_registration(points,points)

    def test_planar_registration_is_identifiable(self):
        source = np.array([[0.,0,0],[1,0,0],[0,1,0],[1,1,0]])
        r = rotation([1.,2,3],1.1)
        target = source@r.T+np.array([4,5,6])
        fitted = fit_registration(source,target)
        np.testing.assert_allclose(fitted['rotation_source_to_target'],r,atol=1e-12)

    def test_csv_invalid_data(self):
        generate(self.path)
        text = (self.path/'tcp.csv').read_text()
        (self.path/'tcp.csv').write_text(text.replace('pose_01','pose_00'))
        with self.assertRaisesRegex(ValueError,'unique'):
            read_csv(self.path/'tcp.csv','tcp')

    def test_nonfinite_points_rejected(self):
        with self.assertRaises(ValueError):
            fit_registration([[0,0,0],[1,0,0],[0,1,float('nan')]], [[0,0,0],[1,0,0],[0,1,0]])


if __name__=='__main__':
    unittest.main(verbosity=2)
