"""PCA compression 55-dim → 15-dim market state vector.

This implementation uses a simple deterministic dimensionality reduction: it
splits the input features into 15 consecutive blocks and averages each block.
This provides a stable 15-dimensional summary vector without requiring a
pretrained PCA artifact, which is sufficient for early-stage analog search.
"""

from __future__ import annotations

from typing import List


N_OUTPUT = 15


def encode(features: List[float]) -> List[float]:
    if not features:
        return [0.0] * N_OUTPUT
    n = len(features)
    block_size = n / N_OUTPUT
    out: List[float] = []
    for i in range(N_OUTPUT):
        start = int(round(i * block_size))
        end = int(round((i + 1) * block_size))
        if start >= end:
            out.append(0.0)
            continue
        block = features[start:end]
        if not block:
            out.append(0.0)
        else:
            out.append(sum(block) / len(block))
    return out
