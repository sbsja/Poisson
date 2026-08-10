"""Compare ten positive duration families under current v6 episode semantics."""

from __future__ import annotations

import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v6_study_common import ScenarioSimulator, level, run_study  # noqa: E402


DISTRIBUTIONS = (
    "gamma", "weibull", "lognormal", "inverse_gaussian",
    "shifted_exponential", "inverse_gamma", "symmetric_two_point",
    "three_point", "pareto", "scaled_beta",
)
LEVELS = [level(name, index, distribution=name)
          for index, name in enumerate(DISTRIBUTIONS)]


def weibull_shape_for_cv(cv: float) -> float:
    target = cv * cv
    lo, hi = 0.08, 100.0
    for _ in range(100):
        mid = (lo + hi) / 2.0
        ratio = math.gamma(1.0 + 2.0 / mid) / (
            math.gamma(1.0 + 1.0 / mid) ** 2
        ) - 1.0
        if ratio > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


class AlternativeDurationRng:
    """Expose ``gammavariate`` while drawing a selected matched-moment family."""

    def __init__(self, base_rng, distribution: str):
        self.base = base_rng
        self.distribution = distribution
        self._weibull_shapes = {}

    def gammavariate(self, shape: float, scale: float) -> float:
        mean = shape * scale
        variance = shape * scale * scale
        standard_deviation = math.sqrt(variance)
        cv = standard_deviation / mean
        name = self.distribution
        if name == "gamma":
            return self.base.gammavariate(shape, scale)
        if name == "weibull":
            key = round(cv, 12)
            weibull_shape = self._weibull_shapes.setdefault(
                key, weibull_shape_for_cv(cv)
            )
            weibull_scale = mean / math.gamma(1.0 + 1.0 / weibull_shape)
            return self.base.weibullvariate(weibull_scale, weibull_shape)
        if name == "lognormal":
            sigma2 = math.log1p(cv * cv)
            mu = math.log(mean) - sigma2 / 2.0
            return self.base.lognormvariate(mu, math.sqrt(sigma2))
        if name == "inverse_gaussian":
            lam = mean ** 3 / variance
            normal = self.base.gauss(0.0, 1.0)
            y = normal * normal
            candidate = (
                mean + (mean * mean * y) / (2.0 * lam)
                - (mean / (2.0 * lam))
                * math.sqrt(4.0 * mean * lam * y + mean * mean * y * y)
            )
            if self.base.random() <= mean / (mean + candidate):
                return candidate
            return mean * mean / candidate
        if name == "shifted_exponential":
            return (mean - standard_deviation) + self.base.expovariate(
                1.0 / standard_deviation
            )
        if name == "inverse_gamma":
            alpha = 2.0 + mean * mean / variance
            beta = mean * (alpha - 1.0)
            return beta / self.base.gammavariate(alpha, 1.0)
        if name == "symmetric_two_point":
            return mean - standard_deviation if self.base.random() < 0.5 else mean + standard_deviation
        if name == "three_point":
            noncentral_probability = (1.0 + cv * cv) / 2.0
            distance = standard_deviation / math.sqrt(noncentral_probability)
            draw = self.base.random()
            if draw < noncentral_probability / 2.0:
                return mean - distance
            if draw < noncentral_probability:
                return mean + distance
            return mean
        if name == "pareto":
            alpha = 1.0 + math.sqrt(1.0 + 1.0 / (cv * cv))
            minimum = mean * (alpha - 1.0) / alpha
            return minimum * self.base.paretovariate(alpha)
        if name == "scaled_beta":
            alpha = 0.5
            beta = (cv * cv * alpha * (alpha + 1.0)) / (
                1.0 - cv * cv * alpha
            )
            maximum = mean * (alpha + beta) / alpha
            return maximum * self.base.betavariate(alpha, beta)
        raise ValueError(f"Unknown duration distribution {name!r}")


def mutate(_cfg, _study_level):
    return None


def simulator_factory(cfg, study_level):
    simulator = ScenarioSimulator(cfg)
    simulator.rng_duration = AlternativeDurationRng(
        simulator.rng_duration, study_level["distribution"]
    )
    return simulator


def main(argv=None):
    return run_study(
        study_file=__file__, study_name="duration_distribution_study",
        description=("Compares ten positive sojourn families. Nine alternatives "
                     "match every element's configured mean and variance to the "
                     "production Gamma law."),
        levels=LEVELS, mutate=mutate, simulator_factory=simulator_factory,
        argv=argv,
    )


if __name__ == "__main__":
    main()
