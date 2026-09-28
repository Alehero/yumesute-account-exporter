"""Lossless MessagePack-CSharp envelope validation. No game SDK dependency."""

from collections import Counter
import lz4.block
import msgpack

LIMIT = 64 * 1024 * 1024
NAMES = {
    0: "User",
    4: "Character",
    5: "CharacterBase",
    11: "Poster",
    25: "Music",
    26: "Accessory",
    27: "Item",
    43: "Costume",
}


def unpack_stream(data):
    if len(data) > LIMIT:
        raise ValueError("Response exceeds size limit")
    decoder = msgpack.Unpacker(raw=False, strict_map_key=False, max_buffer_size=LIMIT)
    decoder.feed(data)
    result, consumed = [], 0
    while True:
        try:
            result.append(decoder.unpack())
            consumed = decoder.tell()
        except msgpack.OutOfData:
            break
    if consumed != len(data):
        raise ValueError("Truncated MessagePack stream")
    return result


def block(data, size):
    if type(size) is not int or not 0 <= size <= LIMIT:
        raise ValueError("Invalid compression length")
    raw = lz4.block.decompress(data, uncompressed_size=size)
    if len(raw) != size:
        raise ValueError("Compression length mismatch")
    return raw


def expand(value):
    if isinstance(value, msgpack.ExtType) and value.code == 99:
        decoder = msgpack.Unpacker(raw=False)
        decoder.feed(value.data)
        size = decoder.unpack()
        values = unpack_stream(block(value.data[decoder.tell() :], size))
        return expand(values[0]) if len(values) == 1 else [expand(v) for v in values]
    if isinstance(value, list):
        if value and isinstance(value[0], msgpack.ExtType) and value[0].code == 98:
            sizes = unpack_stream(value[0].data)
            if len(sizes) == 1 and isinstance(sizes[0], list):
                sizes = sizes[0]
            if (
                len(sizes) != len(value) - 1
                or any(type(n) is not int or n < 0 for n in sizes)
                or sum(sizes) > LIMIT
            ):
                raise ValueError("Invalid compression block array")
            raw = b"".join(block(b, n) for b, n in zip(value[1:], sizes))
            values = unpack_stream(raw)
            return (
                expand(values[0]) if len(values) == 1 else [expand(v) for v in values]
            )
        return [expand(v) for v in value]
    return value


def envelope(data):
    values = [expand(v) for v in unpack_stream(data)]
    if len(values) != 5 or values[0]:
        raise ValueError("Missing or unsuccessful game response envelope")
    return values


def inspect_snapshot(data):
    rows = envelope(data)[1]
    if not isinstance(rows, list):
        raise ValueError("Missing account records")
    counts, users = Counter(), []
    for item in rows:
        if item is None:
            continue
        if (
            not isinstance(item, list)
            or len(item) != 2
            or type(item[0]) is not int
            or not isinstance(item[1], list)
        ):
            raise ValueError("Malformed account record")
        kind, fields = item
        counts[str(kind)] += 1
        if kind == 0:
            users.append(fields)
    if (
        len(users) != 1
        or not users[0]
        or type(users[0][0]) is not int
        or users[0][0] <= 0
    ):
        raise ValueError("Expected exactly one account identity")
    return {
        "user_id": users[0][0],
        "entries": len(rows),
        "null_entries": sum(r is None for r in rows),
        "entity_counts_by_id": dict(counts),
        "summary": {name: counts[str(key)] for key, name in NAMES.items()},
    }
