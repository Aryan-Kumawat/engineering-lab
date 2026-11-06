"""Inspect point-cloud geometry and validate annotation identity without a display."""
import argparse
import json
from cloud import load_cloud, load_annotations, fingerprint

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cloud');parser.add_argument('--labels')
    args=parser.parse_args()
    try:
        points=load_cloud(args.cloud)
        result={'points':len(points),'min_xyz':points.min(0).tolist(),'max_xyz':points.max(0).tolist(),'cloud_sha256':fingerprint(points)}
        if args.labels:result['boxes']=len(load_annotations(args.labels,points))
        print(json.dumps(result,indent=2))
    except (OSError,ValueError,TypeError,UnicodeError) as exc:parser.error(str(exc))
