#!/usr/bin/env python3
"""Structured payload encoding for Paper 1.

Payload layout (16 bytes):
  version         4 bits
  platform_id     8 bits
  generation_id  48 bits
  model_version   8 bits
  timestamp      24 bits (hours since Unix epoch)
  content_hash   16 bits
  reserved        4 bits
  crc16          16 bits

The 16-byte payload is protected by a shortened Reed-Solomon code and then
repeated at the bit level for additional robustness.
"""

from __future__ import annotations

import binascii
import hashlib
import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import reedsolo


RS_PARITY_BYTES = 16
RS_MESSAGE_BYTES = 16
RS_TOTAL_BYTES = RS_MESSAGE_BYTES + RS_PARITY_BYTES
REPEAT_FACTOR = 4

_RS = reedsolo.RSCodec(RS_PARITY_BYTES, nsize=RS_TOTAL_BYTES)


def _int_bits(value: int, width: int) -> list[int]:
    if value < 0:
        value = 0
    value &= (1 << width) - 1
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def _bits_to_int(bits: Iterable[int]) -> int:
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def bits_to_bytes(bits: Iterable[int]) -> bytes:
    bits = list(bits)
    if len(bits) % 8:
        bits += [0] * (8 - len(bits) % 8)
    out = bytearray()
    for i in range(0, len(bits), 8):
        out.append(_bits_to_int(bits[i : i + 8]))
    return bytes(out)


def bytes_to_bits(data: bytes) -> list[int]:
    out = []
    for byte in data:
        out.extend(_int_bits(byte, 8))
    return out


def stable_hash_int(text: str, width: int) -> int:
    digest = hashlib.sha256(str(text).encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big")
    return value & ((1 << width) - 1)


def timestamp_hours(value: str) -> int:
    if not value:
        return 0
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() // 3600)


def file_sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class DecodedPayload:
    version: int
    platform_id: int
    generation_id: int
    model_version: int
    timestamp: int
    content_hash: int
    crc_expected: int
    crc_actual: int
    crc_ok: bool
    rs_success: bool
    rs_corrected: int
    raw_bytes: bytes
    mode: str = "rs_repeat"


def build_payload(
    platform_id: str,
    generation_id: str,
    model_version: str,
    created_at: str,
    content_sha256: str,
    version: int = 1,
) -> bytes:
    header_bits = []
    header_bits += _int_bits(version, 4)
    header_bits += _int_bits(stable_hash_int(platform_id, 8), 8)
    header_bits += _int_bits(stable_hash_int(generation_id, 48), 48)
    header_bits += _int_bits(stable_hash_int(model_version, 8), 8)
    header_bits += _int_bits(timestamp_hours(created_at), 24)
    header_bits += _int_bits(stable_hash_int(content_sha256, 16), 16)
    header_bits += _int_bits(0, 4)
    header = bits_to_bytes(header_bits)
    if len(header) != 14:
        raise RuntimeError(f"Unexpected header length: {len(header)}")
    crc = binascii.crc_hqx(header, 0xFFFF)
    payload = header + struct.pack(">H", crc)
    if len(payload) != RS_MESSAGE_BYTES:
        raise RuntimeError(f"Unexpected payload length: {len(payload)}")
    return payload


def repeat_encode(bits: Iterable[int], repeat: int = REPEAT_FACTOR) -> list[int]:
    out = []
    for bit in bits:
        out.extend([int(bit)] * repeat)
    return out


def repeat_decode(bits: Iterable[int], repeat: int = REPEAT_FACTOR) -> list[int]:
    bits = list(bits)
    if len(bits) % repeat:
        raise ValueError("Coded bit length is not divisible by repeat factor")
    out = []
    for i in range(0, len(bits), repeat):
        chunk = bits[i : i + repeat]
        out.append(1 if sum(chunk) > repeat / 2 else 0)
    return out


def coded_bit_length(repeat: int = REPEAT_FACTOR, mode: str = "rs_repeat") -> int:
    if mode in ("rs_repeat", "rs_only"):
        return RS_TOTAL_BYTES * 8 * (repeat if mode == "rs_repeat" else 1)
    if mode == "repeat_only":
        return RS_MESSAGE_BYTES * 8 * repeat
    if mode == "raw":
        return RS_MESSAGE_BYTES * 8
    raise ValueError(f"Unknown payload mode: {mode}")


def encode_payload(
    payload: bytes, repeat: int = REPEAT_FACTOR, mode: str = "rs_repeat"
) -> list[int]:
    if mode in ("rs_repeat", "rs_only"):
        rs_bytes = _RS.encode(payload)
        bits = bytes_to_bits(rs_bytes)
        return repeat_encode(bits, repeat=repeat) if mode == "rs_repeat" else bits
    payload_bits = bytes_to_bits(payload)
    if mode == "repeat_only":
        return repeat_encode(payload_bits, repeat=repeat)
    if mode == "raw":
        return payload_bits
    raise ValueError(f"Unknown payload mode: {mode}")


def decode_payload(
    coded_bits: Iterable[int],
    repeat: int = REPEAT_FACTOR,
    mode: str = "rs_repeat",
) -> DecodedPayload:
    coded_bits = list(coded_bits)
    rs_success = False
    rs_corrected = 0
    if mode == "rs_repeat":
        majority_bits = repeat_decode(coded_bits, repeat=repeat)
        rs_bytes = bits_to_bytes(majority_bits)[:RS_TOTAL_BYTES]
        payload = rs_bytes[:RS_MESSAGE_BYTES]
        try:
            decoded, _, errata = _RS.decode(bytearray(rs_bytes))
            payload = bytes(decoded[:RS_MESSAGE_BYTES])
            rs_success = True
        except Exception:
            rs_success = False
    elif mode == "rs_only":
        rs_bytes = bits_to_bytes(coded_bits)[:RS_TOTAL_BYTES]
        payload = rs_bytes[:RS_MESSAGE_BYTES]
        try:
            decoded, _, errata = _RS.decode(bytearray(rs_bytes))
            payload = bytes(decoded[:RS_MESSAGE_BYTES])
            rs_success = True
        except Exception:
            rs_success = False
    elif mode == "repeat_only":
        majority_bits = repeat_decode(coded_bits, repeat=repeat)
        payload = bits_to_bytes(majority_bits)[:RS_MESSAGE_BYTES]
    elif mode == "raw":
        payload = bits_to_bytes(coded_bits)[:RS_MESSAGE_BYTES]
    else:
        raise ValueError(f"Unknown payload mode: {mode}")

    header = payload[:14]
    crc_expected = struct.unpack(">H", payload[14:16])[0]
    crc_actual = binascii.crc_hqx(header, 0xFFFF)
    bits = bytes_to_bits(header)
    offset = 0

    version = _bits_to_int(bits[offset : offset + 4]); offset += 4
    platform_id = _bits_to_int(bits[offset : offset + 8]); offset += 8
    generation_id = _bits_to_int(bits[offset : offset + 48]); offset += 48
    model_version = _bits_to_int(bits[offset : offset + 8]); offset += 8
    timestamp = _bits_to_int(bits[offset : offset + 24]); offset += 24
    content_hash = _bits_to_int(bits[offset : offset + 16]); offset += 16

    return DecodedPayload(
        version=version,
        platform_id=platform_id,
        generation_id=generation_id,
        model_version=model_version,
        timestamp=timestamp,
        content_hash=content_hash,
        crc_expected=crc_expected,
        crc_actual=crc_actual,
        crc_ok=(crc_expected == crc_actual),
        rs_success=rs_success,
        rs_corrected=rs_corrected,
        raw_bytes=payload,
        mode=mode,
    )


def bit_error_rate(expected: Iterable[int], actual: Iterable[int]) -> float:
    expected = list(expected)
    actual = list(actual)
    if len(expected) != len(actual):
        return 1.0
    if not expected:
        return 0.0
    return sum(1 for a, b in zip(expected, actual) if a != b) / len(expected)
