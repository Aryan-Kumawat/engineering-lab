import math
import unittest
from playground import Config, simulate


class SimulationTests(unittest.TestCase):
    def test_uncontrolled_load_matches_analytical_response(self):
        c = Config(kp=0, ki=0, kd=0, load_at=0, load=0.3)
        for t, _, speed, _, _ in simulate(c):
            self.assertAlmostEqual(speed, -c.load * (1 - math.exp(-t/c.tau)), places=12)

    def test_saturation_bounds(self):
        rows = simulate(Config(kp=100, ki=30, target=10))
        self.assertTrue(all(abs(row[3]) <= 3 for row in rows))

    def test_pi_rejects_load(self):
        rows = simulate(Config(kd=0, duration=40))
        self.assertLess(abs(rows[-1][1] - rows[-1][2]), 1e-5)

    def test_sampling_consistency(self):
        coarse = simulate(Config(dt=0.01))[-1][2]
        fine = simulate(Config(dt=0.005))[-1][2]
        self.assertLess(abs(coarse-fine), 0.002)

    def test_invalid_inputs(self):
        for c in [Config(dt=0), Config(tau=-1), Config(kp=float('nan')), Config(dt=0.2)]:
            with self.assertRaises(ValueError):
                simulate(c)


if __name__ == '__main__':
    unittest.main()
