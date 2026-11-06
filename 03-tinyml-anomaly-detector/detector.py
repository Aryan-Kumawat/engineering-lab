"""Train a compact quantized sensor detector on reproducible synthetic data."""
import argparse
import json
import math
import random
import statistics
from pathlib import Path


def features(window):
    if not window or not all(math.isfinite(x) for x in window):
        raise ValueError('Window must contain finite samples')
    return [statistics.mean(window), math.sqrt(statistics.mean(x*x for x in window))]


def train(windows):
    vectors = [features(w) for w in windows]
    if len(vectors) < 2:
        raise ValueError('Training requires at least two normal windows')
    centers = [statistics.mean(v[i] for v in vectors) for i in range(2)]
    scales = [max(statistics.stdev(v[i] for v in vectors), 0.01) for i in range(2)]
    # Q12 integer parameters; stored in a portable JSON model.
    return {'version': 1, 'q': 4096, 'center': [round(x*4096) for x in centers],
            'scale': [max(1, round(x*4096)) for x in scales], 'threshold': 5000}


def score(model, window):
    # Features still use floating point; normalized score uses integer arithmetic.
    f = [round(x*model['q']) for x in features(window)]
    return max(abs(f[i]-model['center'][i])*1000//model['scale'][i] for i in range(2))


def dataset(count, seed, anomalous=False):
    rng = random.Random(seed)
    return [[rng.gauss(0, 0.2 if not anomalous else 1.0) + (0.8 if anomalous else 0)
             for _ in range(32)] for _ in range(count)]


def evaluate(model):
    normal = dataset(500, 41)
    bad = dataset(500, 42, True)
    fp = sum(score(model, w) > model['threshold'] for w in normal)
    tp = sum(score(model, w) > model['threshold'] for w in bad)
    return {'normal_windows': len(normal), 'anomaly_windows': len(bad),
            'false_positives': fp, 'true_positives': tp,
            'precision': tp/(tp+fp) if tp+fp else 0, 'recall': tp/len(bad)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', type=Path, default=Path('model.json'))
    parser.add_argument('--window', help='Score one comma-separated window using saved model')
    args = parser.parse_args()
    try:
        if args.window is not None:
            model = json.loads(args.model.read_text())
            value = score(model, [float(x) for x in args.window.split(',')])
            print(json.dumps({'score': value, 'anomaly': value > model['threshold']}))
        else:
            model = train(dataset(1000, 17))
            args.model.write_text(json.dumps(model, indent=2)+'\n')
            print(json.dumps(evaluate(model), indent=2))
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
