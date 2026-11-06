import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
import numpy as np
from cloud import load_cloud, demo_points, annotation_document, save_annotations, load_annotations, validate_box


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)
    def ply(self,body,properties='property float x\nproperty float y\nproperty float z',count=2):
        p=self.path/'cloud.ply';p.write_text(f'ply\nformat ascii 1.0\nelement vertex {count}\n{properties}\nend_header\n'+body);return p
    def test_ply_properties_reordered(self):
        path=self.ply('3 1 2 255\n6 4 5 100\n','property float z\nproperty float x\nproperty float y\nproperty uchar red')
        np.testing.assert_array_equal(load_cloud(path),[[1,2,3],[4,5,6]])
    def test_pcd_ascii(self):
        p=self.path/'cloud.pcd';p.write_text('VERSION .7\nFIELDS x y z intensity\nSIZE 4 4 4 4\nTYPE F F F F\nCOUNT 1 1 1 1\nWIDTH 2\nHEIGHT 1\nPOINTS 2\nDATA ascii\n1 2 3 0\n4 5 6 1\n')
        np.testing.assert_array_equal(load_cloud(p),[[1,2,3],[4,5,6]])
    def test_incomplete_and_nonfinite_clouds_rejected(self):
        for data in ['1 2 3\n','nan 2 3\n4 5 6\n']:
            with self.assertRaises(ValueError):load_cloud(self.ply(data))
    def test_binary_ply_rejected(self):
        p=self.ply('1 2 3\n4 5 6\n');p.write_text(p.read_text().replace('ascii','binary_little_endian'))
        with self.assertRaises(ValueError):load_cloud(p)
    def test_exact_annotation_roundtrip_and_cloud_identity(self):
        points=demo_points();boxes=[{'id':'sample','label':'robot part','min':[-1.123456789,-2.,0.], 'max':[.123456789,2.,3.]}]
        path=self.path/'labels.json';save_annotations(path,points,boxes)
        self.assertEqual(load_annotations(path,points),boxes)
        altered=points.copy();altered[0,0]+=.01
        with self.assertRaisesRegex(ValueError,'identity'):load_annotations(path,altered)
    def test_invalid_boxes_and_duplicate_ids(self):
        box={'id':'b','label':'part','min':[0,0,0],'max':[1,1,1]}
        with self.assertRaises(ValueError):annotation_document(demo_points(),[box,box])
        for change in [{'max':[0,1,1]},{'min':[float('nan'),0,0]},{'label':''}]:
            bad=copy.deepcopy(box);bad.update(change)
            with self.assertRaises(ValueError):validate_box(bad)
    def test_save_validation_preserves_previous_document(self):
        points=demo_points();path=self.path/'labels.json';save_annotations(path,points,[]);before=path.read_bytes()
        with self.assertRaises(ValueError):save_annotations(path,points,[{'id':'bad'}])
        self.assertEqual(path.read_bytes(),before)


if __name__=='__main__':unittest.main(verbosity=2)
