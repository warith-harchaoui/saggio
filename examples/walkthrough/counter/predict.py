"""A deterministic toy workload, so the walkthrough measures the same thing twice.

It does arithmetic and nothing else: no network, no files, no accelerator. That is
the point. A worked example whose numbers move between runs teaches nothing about
the tool that produced them.
"""

from __future__ import annotations

import argparse
import math

from config import num_samples


def one_sample(size: int = 20_000) -> float:
    """Return the sum of the square roots of the first ``size`` integers."""
    return sum(math.sqrt(index + 1) for index in range(size))


def main() -> None:
    """Score the number of samples asked for, and print a checksum."""
    parser = argparse.ArgumentParser(description="Score some samples.")
    parser.add_argument("--num_samples", type=int, default=num_samples)
    arguments = parser.parse_args()
    total = 0.0
    for _ in range(arguments.num_samples):
        total += one_sample()
    print(f"{arguments.num_samples} samples, checksum {total:.3f}")


if __name__ == "__main__":
    main()
