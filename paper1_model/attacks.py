#!/usr/bin/env python3
"""Image perturbations for watermark robustness experiments."""

from __future__ import annotations

import io

import cv2
import numpy as np
from PIL import Image


def ensure_512(image: np.ndarray, size: int = 512) -> np.ndarray:
    if image.shape[:2] == (size, size):
        return image
    return cv2.resize(image, (size, size), interpolation=cv2.INTER_LANCZOS4)


def jpeg_compress(image: np.ndarray, quality: int = 70) -> np.ndarray:
    buffer = io.BytesIO()
    Image.fromarray(image.astype(np.uint8)).save(
        buffer, format="JPEG", quality=quality, subsampling=0
    )
    buffer.seek(0)
    with Image.open(buffer) as decoded:
        return np.asarray(decoded.convert("RGB")).copy()


def resize_attack(image: np.ndarray, scale: float = 0.75) -> np.ndarray:
    h, w = image.shape[:2]
    resized = cv2.resize(
        image,
        (max(32, int(w * scale)), max(32, int(h * scale))),
        interpolation=cv2.INTER_LANCZOS4,
    )
    return ensure_512(resized)


def center_crop(image: np.ndarray, ratio: float = 0.9) -> np.ndarray:
    h, w = image.shape[:2]
    crop_h = max(32, int(h * ratio))
    crop_w = max(32, int(w * ratio))
    top = (h - crop_h) // 2
    left = (w - crop_w) // 2
    cropped = image[top : top + crop_h, left : left + crop_w]
    return ensure_512(cropped)


def gaussian_noise(image: np.ndarray, sigma: float = 5.0, seed: int = 20260910):
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, sigma, image.shape)
    return np.clip(image.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def salt_pepper(image: np.ndarray, amount: float = 0.005, seed: int = 20260910):
    rng = np.random.default_rng(seed)
    output = image.copy()
    count = int(image.shape[0] * image.shape[1] * amount)
    coords = (
        rng.integers(0, image.shape[0], count),
        rng.integers(0, image.shape[1], count),
    )
    output[coords] = 255
    coords = (
        rng.integers(0, image.shape[0], count),
        rng.integers(0, image.shape[1], count),
    )
    output[coords] = 0
    return output


def brightness_contrast(
    image: np.ndarray, brightness: float = 1.05, contrast: float = 1.05
):
    output = image.astype(np.float32) * contrast + (brightness - 1.0) * 255
    return np.clip(output, 0, 255).astype(np.uint8)


def gaussian_blur(image: np.ndarray, ksize: int = 3):
    return cv2.GaussianBlur(image, (ksize, ksize), 0)


def screenshot_sim(
    image: np.ndarray, scale: float = 0.8, jpeg_quality: int = 80
):
    resized = resize_attack(image, scale=scale)
    return jpeg_compress(resized, quality=jpeg_quality)


def _perspective_warp(image: np.ndarray, jitter: float, seed: int):
    """Apply a small, deterministic perspective distortion."""

    h, w = image.shape[:2]
    rng = np.random.default_rng(seed)
    src = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
    offset = rng.uniform(-jitter, jitter, size=(4, 2)) * np.array([w, h])
    dst = src + offset.astype(np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _add_moire(image: np.ndarray, strength: float, seed: int):
    """Add a weak two-frequency moire-like pattern."""

    h, w = image.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(seed)
    f1 = rng.uniform(0.035, 0.065)
    f2 = rng.uniform(0.045, 0.085)
    a1 = rng.uniform(0, np.pi)
    a2 = rng.uniform(0, np.pi)
    p1 = np.sin(2 * np.pi * (f1 * (xx * np.cos(a1) + yy * np.sin(a1))))
    p2 = np.sin(2 * np.pi * (f2 * (xx * np.cos(a2) - yy * np.sin(a2))))
    pattern = (p1 + p2) / 2.0
    output = image.astype(np.float32) + strength * 255.0 * pattern[..., None]
    return np.clip(output, 0, 255).astype(np.uint8)


def real_screen_capture(
    image: np.ndarray,
    seed: int = 20260910,
    scale: float = 0.92,
    perspective_jitter: float = 0.015,
    moire_strength: float = 0.04,
    color_shift: float = 0.03,
    blur_ksize: int = 3,
    noise_sigma: float = 2.0,
    jpeg_quality: int = 85,
):
    """More realistic screen-capture simulation.

    Models display scaling, slight perspective, moire, white-balance/color
    shift, optical blur, sensor noise and recompression.  This is still a
    simulator; the function accepts the same image contract as a real capture
    so external captured files can be evaluated with the same pipeline.
    """

    out = resize_attack(image, scale=scale)
    out = _perspective_warp(out, jitter=perspective_jitter, seed=seed)
    out = _add_moire(out, strength=moire_strength, seed=seed + 1)
    rng = np.random.default_rng(seed + 2)
    gains = 1.0 + rng.uniform(-color_shift, color_shift, size=3)
    out = np.clip(out.astype(np.float32) * gains[None, None, :], 0, 255).astype(np.uint8)
    out = cv2.GaussianBlur(out, (blur_ksize, blur_ksize), 0)
    out = gaussian_noise(out, sigma=noise_sigma, seed=seed + 3)
    out = jpeg_compress(out, quality=jpeg_quality)
    return ensure_512(out)


def print_scan(
    image: np.ndarray,
    seed: int = 20260910,
    scale: float = 0.95,
    perspective_jitter: float = 0.025,
    paper_texture: float = 0.03,
    ink_bleed: float = 0.03,
    blur_ksize: int = 3,
    noise_sigma: float = 4.0,
    gamma: float = 1.05,
    jpeg_quality: int = 80,
):
    """More realistic print-scan simulation.

    Models print scaling, perspective, paper texture/yellowing, ink bleed,
    scanner noise, gamma shift and recompression.  As with screen capture, this
    is a simulator and can be replaced by real scan files at the same API.
    """

    out = resize_attack(image, scale=scale)
    out = _perspective_warp(out, jitter=perspective_jitter, seed=seed)

    h, w = out.shape[:2]
    rng = np.random.default_rng(seed + 1)
    low = rng.normal(0, 1, size=(16, 16)).astype(np.float32)
    texture = cv2.resize(low, (w, h), interpolation=cv2.INTER_CUBIC)
    texture = texture / (np.std(texture) + 1e-6)
    out = np.clip(
        out.astype(np.float32)
        + paper_texture * 255.0 * texture[..., None],
        0,
        255,
    ).astype(np.uint8)
    # Slight paper yellowing: increase red/green, reduce blue.
    tint = np.array([1.01, 1.005, 0.985], dtype=np.float32)
    out = np.clip(out.astype(np.float32) * tint[None, None, :], 0, 255).astype(np.uint8)
    out = cv2.GaussianBlur(out, (blur_ksize, blur_ksize), 0)
    out = np.clip(((out.astype(np.float32) / 255.0) ** gamma) * 255.0, 0, 255).astype(
        np.uint8
    )
    out = gaussian_noise(out, sigma=noise_sigma, seed=seed + 2)
    out = jpeg_compress(out, quality=jpeg_quality)
    return ensure_512(out)


def rotate_small(image: np.ndarray, angle: float = 2.0):
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rotated = cv2.warpAffine(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT,
    )
    return ensure_512(rotated)


def apply_attack(image: np.ndarray, name: str, params: dict | None = None):
    params = params or {}
    if name == "jpeg":
        return jpeg_compress(image, **params)
    if name == "resize":
        return resize_attack(image, **params)
    if name == "crop":
        return center_crop(image, **params)
    if name == "gaussian_noise":
        return gaussian_noise(image, **params)
    if name == "salt_pepper":
        return salt_pepper(image, **params)
    if name == "brightness_contrast":
        return brightness_contrast(image, **params)
    if name == "blur":
        return gaussian_blur(image, **params)
    if name == "screenshot":
        return screenshot_sim(image, **params)
    if name == "real_screen_capture":
        return real_screen_capture(image, **params)
    if name == "print_scan":
        return print_scan(image, **params)
    if name == "rotate":
        return rotate_small(image, **params)
    if name == "crop_jpeg":
        return jpeg_compress(
            center_crop(image, ratio=params.get("crop_ratio", 0.9)),
            quality=params.get("jpeg_quality", 70),
        )
    if name == "resize_jpeg":
        return jpeg_compress(
            resize_attack(image, scale=params.get("scale", 0.75)),
            quality=params.get("jpeg_quality", 70),
        )
    if name == "screenshot_noise":
        return gaussian_noise(
            screenshot_sim(
                image,
                scale=params.get("scale", 0.8),
                jpeg_quality=params.get("jpeg_quality", 80),
            ),
            sigma=params.get("sigma", 3),
        )
    if name == "blur_jpeg":
        return jpeg_compress(
            gaussian_blur(image, ksize=params.get("ksize", 3)),
            quality=params.get("jpeg_quality", 70),
        )
    if name == "crop_resize_jpeg":
        return jpeg_compress(
            resize_attack(
                center_crop(image, ratio=params.get("crop_ratio", 0.9)),
                scale=params.get("scale", 0.8),
            ),
            quality=params.get("jpeg_quality", 70),
        )
    if name == "social_recompress":
        first = jpeg_compress(image, quality=params.get("quality_1", 75))
        resized = resize_attack(first, scale=params.get("scale", 0.9))
        return jpeg_compress(resized, quality=params.get("quality_2", 70))
    if name == "clean":
        return image.copy()
    raise ValueError(f"Unknown attack: {name}")
