"""Bounded local JSONL telemetry collector and replay client. Python 3.10+."""
import argparse
import asyncio
import json
import math
from pathlib import Path

MAX_MESSAGE = 4096


def validate(message):
    if not isinstance(message, dict) or message.get('version') != 1:
        raise ValueError('Expected protocol version 1')
    if not isinstance(message.get('sensor'), str) or not 1 <= len(message['sensor']) <= 64:
        raise ValueError('sensor must be a string of 1..64 characters')
    for field in ['timestamp', 'value']:
        value = message.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'{field} must be finite numeric data')
    if message['timestamp'] < 0:
        raise ValueError('timestamp must be nonnegative')
    return {key: message[key] for key in ['version', 'sensor', 'timestamp', 'value']}


async def serve(host, port, path):
    queue = asyncio.Queue(maxsize=128)
    # Dedicated writer ensures messages from concurrent connections never interleave.
    async def persist():
        with path.open('a', encoding='utf-8') as file:
            while True:
                message, receipt = await queue.get()
                try:
                    file.write(json.dumps(message, allow_nan=False)+'\n')
                    file.flush()
                    if not receipt.done():
                        receipt.set_result(True)
                except OSError as exc:
                    if not receipt.done():
                        receipt.set_exception(exc)
                finally:
                    queue.task_done()

    async def client(reader, writer):
        try:
            while True:
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=30)
                    if not line:
                        break
                    if len(line) > MAX_MESSAGE:
                        raise ValueError('Message exceeds 4096 bytes')
                    message = validate(json.loads(line))
                    receipt = asyncio.get_running_loop().create_future()
                    await queue.put((message, receipt))  # Backpressure, never silent drops.
                    await receipt
                    response = {'ok': True}
                except (ValueError, UnicodeError, OSError) as exc:
                    response = {'ok': False, 'error': str(exc)}
                writer.write((json.dumps(response)+'\n').encode())
                await writer.drain()
        except (ConnectionError, asyncio.TimeoutError):
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    # Fail before accepting clients if the log destination is unavailable.
    with path.open('a', encoding='utf-8'):
        pass
    task = asyncio.create_task(persist())
    try:
        server = await asyncio.start_server(client, host, port, limit=MAX_MESSAGE)
        print(f'Listening on {host}:{port}; log={path}', flush=True)
        async with server:
            await server.serve_forever()
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def replay(host, port, path):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        with path.open(encoding='utf-8') as file:
            for number, line in enumerate(file, 1):
                message = validate(json.loads(line))
                payload = (json.dumps(message)+'\n').encode()
                if len(payload) > MAX_MESSAGE:
                    raise ValueError(f'Row {number} too large')
                writer.write(payload)
                await writer.drain()
                reply = await asyncio.wait_for(reader.readline(), 10)
                if not reply or not json.loads(reply).get('ok'):
                    raise ValueError(f'Collector did not acknowledge row {number}: {reply!r}')
                print(f'ack {number}')
    finally:
        writer.close()
        await writer.wait_closed()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['serve', 'replay'])
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--file', type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be 1..65535')
    try:
        asyncio.run((serve if args.mode == 'serve' else replay)(args.host, args.port, args.file))
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, asyncio.TimeoutError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
