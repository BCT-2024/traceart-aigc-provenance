#!/usr/bin/env python3
"""Database matching and three-level trust scoring."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from payload import (
    RS_TOTAL_BYTES,
    REPEAT_FACTOR,
    bit_error_rate,
    build_payload,
    coded_bit_length,
    decode_payload,
    encode_payload,
    stable_hash_int,
    timestamp_hours,
)
from watermark import extract_bits, load_rgb


HIGH_TRUST_THRESHOLD = 0.55
MEDIUM_TRUST_THRESHOLD = 0.32
# Content binding is a hard gate: the watermark payload must belong to the
# same image content as the matched registration record.  The threshold is
# calibrated from ORB matching on legitimate attacked positives vs copy attacks.
CONTENT_BINDING_THRESHOLD = 0.30
CONTENT_BINDING_FLAT_THRESHOLD = 0.90
CONTENT_BINDING_MIN_KEYPOINTS = 10


@dataclass
class DatabaseRecord:
    generation_id: str
    generation_id_hash: int
    platform_id: str
    platform_hash: int
    model_version: str
    model_hash: int
    created_at: str
    timestamp: int
    content_sha256: str
    content_hash: int
    average_hash: bytes
    flat_signature: bytes = b""
    orb_descriptors: bytes = b""
    orb_keypoint_count: int = 0


def average_hash(image: np.ndarray, hash_size: int = 8) -> bytes:
    gray = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    gray = cv2.resize(gray, (hash_size, hash_size), interpolation=cv2.INTER_AREA)
    bits = (gray > gray.mean()).astype(np.uint8).flatten()
    return np.packbits(bits).tobytes()


def flat_signature(image: np.ndarray, size: int = 8) -> bytes:
    """Low-frequency color/layout signature for texture-poor images.

    Average hash can collapse to the same value for different solid colors.
    This 8x8 RGB signature preserves coarse color and layout information and
    is quantised to 16 levels per channel.
    """

    resized = cv2.resize(image.astype(np.uint8), (size, size), interpolation=cv2.INTER_AREA)
    quantised = np.clip(np.rint(resized.astype(np.float32) / 17.0), 0, 15).astype(
        np.uint8
    )
    return quantised.tobytes()


def flat_signature_similarity(image: np.ndarray, record: DatabaseRecord) -> float:
    if not record.flat_signature:
        return 0.0
    query = np.frombuffer(flat_signature(image), dtype=np.uint8).astype(np.float32)
    reference = np.frombuffer(record.flat_signature, dtype=np.uint8).astype(np.float32)
    if query.size != reference.size or query.size == 0:
        return 0.0
    return float(1.0 - np.mean(np.abs(query - reference)) / 15.0)


_ORB = cv2.ORB_create(nfeatures=800, fastThreshold=10)


def _orb_features(image: np.ndarray) -> tuple[bytes, int]:
    """Return ORB descriptors and keypoint count for content binding."""

    gray = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY)
    try:
        keypoints, descriptors = _ORB.detectAndCompute(gray, None)
    except cv2.error:
        # Some extremely flat images make ORB's internal pyramid fail.
        # Returning empty features lets the verifier use the hash fallback.
        return b"", 0
    if descriptors is None or len(keypoints) == 0:
        return b"", 0
    return descriptors.tobytes(), len(keypoints)


def _descriptor_array(descriptors: bytes) -> np.ndarray | None:
    if not descriptors:
        return None
    array = np.frombuffer(descriptors, dtype=np.uint8)
    if array.size % 32:
        return None
    return array.reshape(-1, 32)


def content_binding_details(image: np.ndarray, record: DatabaseRecord) -> dict:
    """Return content-binding evidence and the fallback method used.

    ORB is used because it is robust to JPEG, resize, crop and screenshot-like
    transformations while remaining very discriminative between different
    images.  If either side has too few ORB keypoints, fall back to the average
    hash so that flat images do not become unconditional false negatives.
    """

    query_descriptors, query_count = _orb_features(image)
    query = _descriptor_array(query_descriptors)
    reference = _descriptor_array(record.orb_descriptors)
    if (
        query is None
        or reference is None
        or query_count < CONTENT_BINDING_MIN_KEYPOINTS
        or record.orb_keypoint_count < CONTENT_BINDING_MIN_KEYPOINTS
        or len(query) < 2
        or len(reference) < 2
    ):
        hash_score = float(hamming_similarity(average_hash(image), record.average_hash))
        signature_score = flat_signature_similarity(image, record)
        return {
            "score": float(0.5 * hash_score + 0.5 * signature_score),
            "method": "flat_signature_fallback",
            "query_keypoints": int(query_count),
            "reference_keypoints": int(record.orb_keypoint_count),
            "good_matches": 0,
        }

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    try:
        pairs = matcher.knnMatch(query, reference, k=2)
    except cv2.error:
        hash_score = float(hamming_similarity(average_hash(image), record.average_hash))
        signature_score = flat_signature_similarity(image, record)
        return {
            "score": float(0.5 * hash_score + 0.5 * signature_score),
            "method": "flat_signature_fallback",
            "query_keypoints": int(query_count),
            "reference_keypoints": int(record.orb_keypoint_count),
            "good_matches": 0,
        }
    good = 0
    for pair in pairs:
        if not pair:
            continue
        best = pair[0].distance
        if len(pair) == 2:
            second = pair[1].distance
            # A strict absolute distance accepts identical/duplicated
            # descriptors where the second-nearest distance is also zero.
            if best <= 32 or best < 0.75 * second:
                good += 1
        elif best <= 32:
            good += 1
    denominator = max(1, min(query_count, record.orb_keypoint_count))
    return {
        "score": float(good / denominator),
        "method": "orb",
        "query_keypoints": int(query_count),
        "reference_keypoints": int(record.orb_keypoint_count),
        "good_matches": int(good),
    }


def content_binding_score(image: np.ndarray, record: DatabaseRecord) -> float:
    """Return only the content-binding score for compatibility/ablation use."""

    return float(content_binding_details(image, record)["score"])


def hamming_similarity(left: bytes, right: bytes) -> float:
    if not left or not right:
        return 0.0
    left_bits = np.unpackbits(np.frombuffer(left, dtype=np.uint8))
    right_bits = np.unpackbits(np.frombuffer(right, dtype=np.uint8))
    if len(left_bits) != len(right_bits):
        return 0.0
    distance = int(np.count_nonzero(left_bits != right_bits))
    return 1.0 - distance / len(left_bits)


def build_database(rows, base_path: Path):
    records = []
    for row in rows:
        if row.get("sample_group") != "positive":
            continue
        image_path = base_path / row["relative_path"]
        image = load_rgb(image_path, size=512)
        orb_descriptors, orb_keypoint_count = _orb_features(image)
        records.append(
            DatabaseRecord(
                generation_id=row["generation_id"],
                generation_id_hash=stable_hash_int(row["generation_id"], 48),
                platform_id=row["platform_id"],
                platform_hash=stable_hash_int(row["platform_id"], 8),
                model_version=row["model_version"],
                model_hash=stable_hash_int(row["model_version"], 8),
                created_at=row["created_at"],
                timestamp=timestamp_hours(row["created_at"]),
                content_sha256=row["sha256"],
                content_hash=stable_hash_int(row["sha256"], 16),
                average_hash=average_hash(image),
                flat_signature=flat_signature(image),
                orb_descriptors=orb_descriptors,
                orb_keypoint_count=orb_keypoint_count,
            )
        )
    return records


def _field_consistency(payload, record: DatabaseRecord) -> float:
    checks = [
        payload.generation_id == record.generation_id_hash,
        payload.platform_id == record.platform_hash,
        payload.model_version == record.model_hash,
        abs(payload.timestamp - record.timestamp) <= 24,
        payload.content_hash == record.content_hash,
    ]
    return sum(1.0 for ok in checks if ok) / len(checks)


def _trust_level(score: float) -> str:
    if score >= HIGH_TRUST_THRESHOLD:
        return "high"
    if score >= MEDIUM_TRUST_THRESHOLD:
        return "medium"
    return "low"


def alignment_candidates(image: np.ndarray, scales=(0.80, 0.85, 0.875, 0.90, 0.925, 0.95, 1.05)):
    h, w = image.shape[:2]
    candidates = [("identity", image)]
    for scale in scales:
        new_size = max(64, int(h * scale))
        resized = cv2.resize(
            image, (new_size, new_size), interpolation=cv2.INTER_LANCZOS4
        )
        if new_size < h:
            pad_total = h - new_size
            top = pad_total // 2
            bottom = pad_total - top
            left = pad_total // 2
            right = pad_total - left
            for border_name, border_type in [
                ("edge", cv2.BORDER_REPLICATE),
                ("reflect", cv2.BORDER_REFLECT),
            ]:
                canvas = cv2.copyMakeBorder(
                    resized,
                    top,
                    bottom,
                    left,
                    right,
                    border_type,
                )
                candidates.append((f"scale_{scale}_{border_name}", canvas))
        elif new_size > h:
            top = (new_size - h) // 2
            left = (new_size - w) // 2
            candidates.append(
                (f"scale_{scale}", resized[top : top + h, left : left + w])
            )
    return candidates


def _evaluate_decoded(
    image: np.ndarray,
    decoded,
    extracted,
    database: list[DatabaseRecord],
    expected_bits,
    alignment: str,
    verification_mode: str = "joint",
    content_binding_required: bool = True,
    content_binding_threshold: float = CONTENT_BINDING_THRESHOLD,
):
    image_hash = average_hash(image)
    candidates = []
    for record in database:
        field_score = _field_consistency(decoded, record)
        hash_score = hamming_similarity(image_hash, record.average_hash)
        candidate_score = 0.45 * field_score + 0.25 * hash_score
        generation_match = decoded.generation_id == record.generation_id_hash
        if generation_match:
            candidate_score += 0.30
        candidates.append(
            {
                "record": record,
                "field_score": field_score,
                "hash_score": hash_score,
                "candidate_score": candidate_score,
                "generation_match": generation_match,
            }
        )

    best = None
    if candidates:
        # Prefer the record whose generation_id was actually decoded; content
        # binding must be checked against that record, not merely the highest
        # weighted candidate.
        candidates.sort(
            key=lambda item: (item["generation_match"], item["candidate_score"]),
            reverse=True,
        )
        best = candidates[0]

    if best is None:
        return {
            "generation_id": decoded.generation_id,
            "generation_match": False,
            "rs_success": decoded.rs_success,
            "crc_ok": decoded.crc_ok,
            "field_score": 0.0,
            "hash_score": 0.0,
            "score": 0.0,
            "trust": "low",
            "success": False,
            "content_binding_score": 0.0,
            "content_binding_ok": False,
            "content_binding_required": bool(content_binding_required),
            "content_binding_threshold": float(content_binding_threshold),
            "content_binding_effective_threshold": float(content_binding_threshold),
            "content_binding_flat_mode": False,
            "content_binding_method": "none",
            "ber": bit_error_rate(expected_bits, extracted)
            if expected_bits is not None
            else None,
            "alignment": alignment,
            "verification_mode": verification_mode,
        }

    generation_match = bool(best["generation_match"])
    content_details = content_binding_details(image, best["record"])
    content_score = float(content_details["score"])
    flat_mode = content_details["method"] == "flat_signature_fallback"
    effective_content_threshold = (
        CONTENT_BINDING_FLAT_THRESHOLD if flat_mode else content_binding_threshold
    )
    content_ok = bool(content_score >= effective_content_threshold)
    if verification_mode == "watermark_only":
        score = 0.60 * float(decoded.crc_ok) + 0.40 * float(decoded.rs_success)
        if decoded.mode in ("repeat_only", "raw"):
            success = bool(decoded.crc_ok and _trust_level(score) != "low")
        else:
            success = bool(
                decoded.crc_ok
                and decoded.rs_success
                and _trust_level(score) != "low"
            )
    elif verification_mode == "db_only":
        score = (
            0.60 * best["field_score"]
            + 0.30 * best["hash_score"]
            + 0.10 * float(generation_match)
        )
        success = bool(
            generation_match
            and _trust_level(score) != "low"
            and (content_ok or not content_binding_required)
        )
    else:
        score = (
            0.25 * float(decoded.crc_ok)
            + 0.20 * float(decoded.rs_success)
            + 0.30 * best["field_score"]
            + 0.15 * best["hash_score"]
            + 0.10 * float(generation_match)
        )
        if decoded.mode in ("repeat_only", "raw"):
            success = bool(
                decoded.crc_ok
                and generation_match
                and _trust_level(score) != "low"
                and (content_ok or not content_binding_required)
            )
        else:
            success = bool(
                decoded.crc_ok
                and decoded.rs_success
                and generation_match
                and _trust_level(score) != "low"
                and (content_ok or not content_binding_required)
            )
    return {
        "generation_id": decoded.generation_id,
        "matched_generation_id": best["record"].generation_id,
        "generation_match": generation_match,
        "rs_success": decoded.rs_success,
        "crc_ok": decoded.crc_ok,
        "field_score": best["field_score"],
        "hash_score": best["hash_score"],
        "content_binding_score": content_score,
        "content_binding_ok": content_ok,
        "content_binding_method": content_details["method"],
        "content_binding_query_keypoints": content_details["query_keypoints"],
        "content_binding_reference_keypoints": content_details["reference_keypoints"],
        "content_binding_good_matches": content_details["good_matches"],
        "content_binding_required": bool(content_binding_required),
        "content_binding_threshold": float(content_binding_threshold),
        "content_binding_effective_threshold": float(effective_content_threshold),
        "content_binding_flat_mode": bool(flat_mode),
        "score": score,
        "trust": _trust_level(score),
        "success": success,
        "ber": bit_error_rate(expected_bits, extracted)
        if expected_bits is not None
        else None,
        "alignment": alignment,
        "verification_mode": verification_mode,
    }


def verify_image(
    image: np.ndarray,
    database: list[DatabaseRecord],
    seed: int = 20260910,
    repeat: int = REPEAT_FACTOR,
    expected_bits=None,
    carrier: str = "dwt_dct",
    mode: str = "rs_repeat",
    verification_mode: str = "joint",
    content_binding_required: bool = True,
    content_binding_threshold: float = CONTENT_BINDING_THRESHOLD,
):
    num_bits = coded_bit_length(repeat=repeat, mode=mode)
    candidates = alignment_candidates(image)

    best_result = None
    for alignment, candidate_image in candidates:
        extracted = extract_bits(
            candidate_image, num_bits=num_bits, seed=seed, carrier=carrier
        )
        decoded = decode_payload(extracted, repeat=repeat, mode=mode)
        result = _evaluate_decoded(
            candidate_image,
            decoded,
            extracted,
            database,
            expected_bits,
            alignment,
            verification_mode=verification_mode,
            content_binding_required=content_binding_required,
            content_binding_threshold=content_binding_threshold,
        )
        if best_result is None or result["score"] > best_result["score"]:
            best_result = result
        if (
            result["crc_ok"]
            and result["rs_success"]
            and result["generation_match"]
            and result["trust"] == "high"
            and verification_mode == "joint"
            and (result["content_binding_ok"] or not content_binding_required)
        ):
            return result

    return best_result


def encode_for_row(row, repeat: int = REPEAT_FACTOR, mode: str = "rs_repeat"):
    payload = build_payload(
        row["platform_id"],
        row["generation_id"],
        row["model_version"],
        row["created_at"],
        row["sha256"],
    )
    return payload, encode_payload(payload, repeat=repeat, mode=mode)
