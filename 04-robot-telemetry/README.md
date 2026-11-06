# Robot Telemetry Toolkit

A local TCP collector with a versioned JSON Lines protocol, bounded ingestion queue and replay client. Python 3.10+, no pip dependencies.

Terminal 1:

```sh
python telemetry.py serve --file telemetry.jsonl
```

Terminal 2:

```sh
python telemetry.py replay --file samples.jsonl
```

The replay client prints an acknowledgement for each accepted record. Inspect `telemetry.jsonl` to see stored samples. The client waits for each acknowledgement, preserving source order on that connection. Multiple clients may connect concurrently; their messages can interleave in the log.

## Protocol

One UTF-8 JSON object and newline per message, at most 4096 bytes including newline:

```json
{"version":1,"sensor":"motor.speed","timestamp":1.5,"value":0.7}
```

Sensor names contain 1–64 characters. Timestamps are nonnegative; both numeric fields must be finite. Unknown fields are discarded. An acknowledgement is `{"ok":true}` or an error object. Duplicates and out-of-order timestamps are accepted so recorded historical streams can be replayed.

## Reliability decisions

A queue of 128 messages applies backpressure when logging falls behind. A single writer prevents interleaved JSON records. Successful acknowledgement follows a write and flush; it does not mean fsync durability. Idle clients disconnect after 30 seconds. Oversized frames produce errors or disconnection. The replay client uses a ten-second acknowledgement timeout.

There is no automatic retry: reconnecting after an ambiguous acknowledgement could duplicate a sample. Exactly-once delivery would require message IDs, a deduplication store and a resume protocol. Abrupt shutdown can lose unacknowledged records. File writes are synchronous, suitable for modest local experiments, not high-rate production ingestion.

## Scope

The collector binds to localhost by default. There is no authentication, TLS, log rotation or global connection limit. Use it as a local teaching tool. A next experiment can compare throughput and queue delay before choosing a different persistence strategy.
