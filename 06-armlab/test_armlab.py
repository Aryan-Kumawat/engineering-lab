import math
import unittest
from armlab import fk,ik,trajectory

class ArmTests(unittest.TestCase):
    def test_inverse_roundtrip(self):
        for lengths in [(150,110),(1,1),(1,3)]:
            for joints in [(0,0),(.8,1.2),(-2,-.5),(0,math.pi)]:
                target=fk(lengths,joints)[1]
                for branch in [-1,1]:
                    actual=fk(lengths,ik(lengths,target,branch))[1]
                    self.assertAlmostEqual(actual[0],target[0],places=6)
                    self.assertAlmostEqual(actual[1],target[1],places=6)
    def test_reach_limits(self):
        for target in [(300,0),(0,0)]:
            with self.assertRaises(ValueError):ik((150,110),target)
    def test_path_endpoints(self):
        start=(.5,.7);end=ik((150,110),(160,100))
        rows=trajectory(start,end)
        self.assertEqual(rows[0][1:],start)
        tip=fk((150,110),rows[-1][1:])[1]
        self.assertAlmostEqual(tip[0],160)
        self.assertAlmostEqual(tip[1],100)
        self.assertEqual(rows[-1][0],3)

if __name__=='__main__':unittest.main()
