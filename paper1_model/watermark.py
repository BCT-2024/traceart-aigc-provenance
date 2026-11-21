#!/usr/bin/env python3
"""DWT+DCT blind watermark embedding and extraction."""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

import cv2
import numpy as np
import pywt
from PIL import Image


BLOCK_SIZE = 8
DWT_WAVELET = "haar"
PAIR_1 = (3, 2)
PAIR_2 = (2, 3)


def load_rgb(path, size: int | None = 512):
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        if size is not None and rgb.size != (size, size):
            rgb = rgb.resize((size, size), Image.Resampling.LANCZOS)
        return np.asarray(rgb).copy()


def save_rgb(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rgb = np.clip(image, 0, 255).astype(np.uint8)
    if path.suffix.lower() == ".png":
        Image.fromarray(rgb).save(path, optimize=True)
    else:
        Image.fromarray(rgb).save(path, quality=95, subsampling=0, optimize=True)


def block_grid(shape):
    rows = shape[0] // BLOCK_SIZE
    cols = shape[1] // BLOCK_SIZE
    return rows, cols


def block_positions(shape):
    rows, cols = block_grid(shape)
    positions = []
    for r in range(rows):
        for c in range(cols):
            positions.append((r * BLOCK_SIZE, c * BLOCK_SIZE))
    return positions


@lru_cache(maxsize=16)
def block_key(n_blocks: int, seed: int):
    return np.random.default_rng(seed).permutation(n_blocks)


def _embed_one_block(block, bit, alpha):
    dct = cv2.dct(block.astype(np.float32))
    c1 = float(dct[PAIR_1])
    c2 = float(dct[PAIR_2])
    target = alpha if bit else -alpha
    delta = (target - (c1 - c2)) / 2.0
    dct[PAIR_1] = c1 + delta
    dct[PAIR_2] = c2 - delta
    return cv2.idct(dct)


def _extract_one_block(block):
    dct = cv2.dct(block.astype(np.float32))
    return 1 if float(dct[PAIR_1]) - float(dct[PAIR_2]) > 0 else 0


def _embed_dwt_dct(image, bits, seed, alpha):
    ycbcr = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycbcr[:, :, 0]
    c_a, (c_h, c_v, c_d) = pywt.dwt2(y, DWT_WAVELET)
    positions = block_positions(c_a.shape)
    if len(bits) > len(positions):
        raise ValueError(f"Payload too large: {len(bits)} bits > {len(positions)} blocks")

    selected = block_key(len(positions), seed)[: len(bits)]
    c_a_modified = c_a.copy()
    for bit, block_index in zip(bits, selected):
        row, col = positions[int(block_index)]
        block = c_a_modified[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE]
        c_a_modified[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE] = _embed_one_block(
            block, bit, alpha
        )

    y_modified = pywt.idwt2((c_a_modified, (c_h, c_v, c_d)), DWT_WAVELET)
    y_modified = np.clip(y_modified, 0, 255)
    ycbcr[:, :, 0] = y_modified
    return cv2.cvtColor(ycbcr.astype(np.uint8), cv2.COLOR_YCrCb2RGB)


def _extract_dwt_dct(image, num_bits, seed):
    ycbcr = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
    y = ycbcr[:, :, 0].astype(np.float32)
    c_a, _ = pywt.dwt2(y, DWT_WAVELET)
    positions = block_positions(c_a.shape)
    if num_bits > len(positions):
        raise ValueError(f"Requested {num_bits} bits > {len(positions)} blocks")

    selected = block_key(len(positions), seed)[:num_bits]
    bits = []
    for block_index in selected:
        row, col = positions[int(block_index)]
        block = c_a[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE]
        bits.append(_extract_one_block(block))
    return bits


def _embed_dct_only(image, bits, seed, alpha):
    ycbcr = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycbcr[:, :, 0].copy()
    positions = block_positions(y.shape)
    if len(bits) > len(positions):
        raise ValueError(f"Payload too large: {len(bits)} bits > {len(positions)} blocks")
    selected = block_key(len(positions), seed)[: len(bits)]
    for bit, block_index in zip(bits, selected):
        row, col = positions[int(block_index)]
        block = y[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE]
        y[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE] = _embed_one_block(
            block, bit, alpha
        )
    ycbcr[:, :, 0] = np.clip(y, 0, 255)
    return cv2.cvtColor(ycbcr.astype(np.uint8), cv2.COLOR_YCrCb2RGB)


def _extract_dct_only(image, num_bits, seed):
    ycbcr = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
    y = ycbcr[:, :, 0].astype(np.float32)
    positions = block_positions(y.shape)
    selected = block_key(len(positions), seed)[:num_bits]
    bits = []
    for block_index in selected:
        row, col = positions[int(block_index)]
        block = y[row : row + BLOCK_SIZE, col : col + BLOCK_SIZE]
        bits.append(_extract_one_block(block))
    return bits


def _dwt_coefficient_pairs(shape):
    flat_size = int(np.prod(shape))
    return flat_size // 2


def _embed_dwt_only(image, bits, seed, alpha):
    ycbcr = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb).astype(np.float32)
    y = ycbcr[:, :, 0]
    c_a, (c_h, c_v, c_d) = pywt.dwt2(y, DWT_WAVELET)
    flat = c_a.reshape(-1).copy()
    pair_count = _dwt_coefficient_pairs(c_a.shape)
    if len(bits) > pair_count:
        raise ValueError(f"Payload too large: {len(bits)} bits > {pair_count} pairs")
    selected = block_key(pair_count, seed)[: len(bits)]
    for bit, pair_index in zip(bits, selected):
        idx = int(pair_index) * 2
        c1 = float(flat[idx])
        c2 = float(flat[idx + 1])
        target = alpha if bit else -alpha
        delta = (target - (c1 - c2)) / 2.0
        flat[idx] = c1 + delta
        flat[idx + 1] = c2 - delta
    c_a_modified = flat.reshape(c_a.shape)
    y_modified = pywt.idwt2((c_a_modified, (c_h, c_v, c_d)), DWT_WAVELET)
    ycbcr[:, :, 0] = np.clip(y_modified, 0, 255)
    return cv2.cvtColor(ycbcr.astype(np.uint8), cv2.COLOR_YCrCb2RGB)


def _extract_dwt_only(image, num_bits, seed):
    ycbcr = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
    y = ycbcr[:, :, 0].astype(np.float32)
    c_a, _ = pywt.dwt2(y, DWT_WAVELET)
    flat = c_a.reshape(-1)
    pair_count = _dwt_coefficient_pairs(c_a.shape)
    selected = block_key(pair_count, seed)[:num_bits]
    bits = []
    for pair_index in selected:
        idx = int(pair_index) * 2
        bits.append(1 if flat[idx] - flat[idx + 1] > 0 else 0)
    return bits


def _embed_lsb(image, bits, seed, alpha=None):
    ycbcr = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb).astype(np.uint8)
    y = ycbcr[:, :, 0].reshape(-1).copy()
    selected = block_key(y.size, seed)[: len(bits)]
    y[selected] = (y[selected] & 0xFE) | np.asarray(bits, dtype=np.uint8)
    ycbcr[:, :, 0] = y.reshape(ycbcr[:, :, 0].shape)
    return cv2.cvtColor(ycbcr, cv2.COLOR_YCrCb2RGB)


def _extract_lsb(image, num_bits, seed):
    ycbcr = cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
    y = ycbcr[:, :, 0].reshape(-1)
    selected = block_key(y.size, seed)[:num_bits]
    return [int(y[idx] & 1) for idx in selected]


def embed_bits(
    image,
    bits,
    seed: int = 20260910,
    alpha: float = 12.0,
    carrier: str = "dwt_dct",
):
    if carrier == "dwt_dct":
        return _embed_dwt_dct(image, bits, seed, alpha)
    if carrier == "dct_only":
        return _embed_dct_only(image, bits, seed, alpha)
    if carrier == "dwt_only":
        return _embed_dwt_only(image, bits, seed, alpha)
    if carrier == "lsb":
        return _embed_lsb(image, bits, seed, alpha)
    raise ValueError(f"Unknown carrier: {carrier}")


def extract_bits(
    image,
    num_bits: int,
    seed: int = 20260910,
    carrier: str = "dwt_dct",
):
    if carrier == "dwt_dct":
        return _extract_dwt_dct(image, num_bits, seed)
    if carrier == "dct_only":
        return _extract_dct_only(image, num_bits, seed)
    if carrier == "dwt_only":
        return _extract_dwt_only(image, num_bits, seed)
    if carrier == "lsb":
        return _extract_lsb(image, num_bits, seed)
    raise ValueError(f"Unknown carrier: {carrier}")


def psnr(reference, image):
    reference = reference.astype(np.float64)
    image = image.astype(np.float64)
    mse = np.mean((reference - image) ** 2)
    if mse == 0:
        return float("inf")
    return 10.0 * np.log10((255.0 ** 2) / mse)


def ssim(reference, image):
    x = cv2.cvtColor(reference.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float64)
    y = cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float64)
    mu_x = x.mean()
    mu_y = y.mean()
    var_x = x.var()
    var_y = y.var()
    cov = ((x - mu_x) * (y - mu_y)).mean()
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    return ((2 * mu_x * mu_y + c1) * (2 * cov + c2)) / (
        (mu_x ** 2 + mu_y ** 2 + c1) * (var_x + var_y + c2)
    )
