"""Reproducible importer benchmark; does not measure viewer FPS."""
import argparse
import json
import platform
import tempfile
import time
from pathlib import Path
import numpy as np
from cloud import load_cloud, fingerprint

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--points',type=int,default=100000);args=parser.parse_args()
    if not 1<=args.points<=1000000:parser.error('Use 1..1,000,000 points')
    points=np.random.default_rng(33).normal(size=(args.points,3))
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'benchmark.ply'
        with path.open('w') as file:
            file.write(f'ply\nformat ascii 1.0\nelement vertex {len(points)}\nproperty float x\nproperty float y\nproperty float z\nend_header\n')
            np.savetxt(file,points,fmt='%.8f')
        start=time.perf_counter();loaded=load_cloud(path);load_time=time.perf_counter()-start
        start=time.perf_counter();fingerprint(loaded);hash_time=time.perf_counter()-start
        print(json.dumps({'points':len(loaded),'input_bytes':path.stat().st_size,'import_seconds':load_time,'fingerprint_seconds':hash_time,
                          'python':platform.python_version(),'numpy':np.__version__,'platform':platform.platform(),
                          'scope':'Single warm-environment importer run; not a rendering benchmark'},indent=2))
