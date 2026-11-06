"""Focused integration checks for projects 03–05. Run from repository root."""
import asyncio
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectChecks(unittest.TestCase):
    def test_detector_holdout_and_invalid_samples(self):
        d = load('detector', '03-tinyml-anomaly-detector/detector.py')
        model = d.train(d.dataset(1000, 17))
        result = d.evaluate(model)
        self.assertGreater(result['recall'], 0.95)
        self.assertLess(result['false_positives'], 25)
        self.assertEqual(model, json.loads(json.dumps(model)))
        with self.assertRaises(ValueError):
            d.features([float('nan')])

    def test_search_citations_and_reindex(self):
        e = load('explorer', '05-local-codebase-intelligence/explorer.py')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root/'source'; source.mkdir()
            (source/'motor.py').write_text('def speed_controller():\n    return 42\n')
            (source/'.env').write_text('hidden_secret')
            db = root/'index.sqlite'
            self.assertEqual(e.index(source, db)['files'], 1)
            result = e.search(db, 'speed_controller')
            self.assertEqual(result[0]['citation'], 'motor.py:1-2')
            self.assertEqual(e.search(db, 'unfindableword'), [])
            (source/'motor.py').unlink()
            e.index(source, db)
            self.assertEqual(e.search(db, 'speed_controller'), [])

    def test_telemetry_validation(self):
        t = load('telemetry', '04-robot-telemetry/telemetry.py')
        for message in [{}, {'version':1, 'sensor':'s', 'timestamp':0, 'value':True}]:
            with self.assertRaises(ValueError):
                t.validate(message)

    def test_telemetry_replay_roundtrip(self):
        t = load('telemetry_roundtrip', '04-robot-telemetry/telemetry.py')
        async def run():
            with tempfile.TemporaryDirectory() as temp:
                target = Path(temp)/'log.jsonl'
                # Reserve an ephemeral port for this isolated local check.
                import socket
                sock = socket.socket(); sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]; sock.close()
                task = asyncio.create_task(t.serve('127.0.0.1', port, target))
                try:
                    for _ in range(50):
                        await asyncio.sleep(0.01)
                        if task.done():
                            await task
                        try:
                            await t.replay('127.0.0.1', port, ROOT/'04-robot-telemetry/samples.jsonl')
                            break
                        except ConnectionRefusedError:
                            continue
                    else:
                        self.fail('Collector did not start')
                    records = [json.loads(line) for line in target.read_text().splitlines()]
                    self.assertEqual(len(records), 3)
                    self.assertEqual(records[-1]['value'], 0.95)
                finally:
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main(verbosity=2)
