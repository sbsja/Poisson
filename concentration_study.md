# Concentration-Scale Study (Dirichlet transition vectors)

Question: what `concentration_scale` (c) should be used in `alpha = c * normalized_weights`?

## Analytical result

A layer's realized unknown probability mass is Beta(c*p, c*(1-p)) with p = 0.004 (designed mass, exact by construction of the calculated unknown weight). Its standard deviation is sqrt(p(1-p)/(c+1)):

| c | std of realized mass | CV (std/p) |
|---|---|---|
| 100 | 6.28e-03 | 1.57 |
| 300 | 3.64e-03 | 0.91 |
| 1,000 | 1.99e-03 | 0.50 |
| 3,000 | 1.15e-03 | 0.29 |
| 10,000 | 6.31e-04 | 0.16 |
| 20,000 | 4.46e-04 | 0.11 |
| 30,000 | 3.64e-04 | 0.09 |
| 100,000 | 2.00e-04 | 0.05 |

At the old default c = 100 the CV is ~1.6: the scatter is larger than the target itself, which is exactly why individual layers in earlier runs landed anywhere between ~0.003% and ~0.5%. The variance is a property of the single Dirichlet draw made at initialization, not of simulation length.

## Monte Carlo sweep

4000 Dirichlet draws per value of c, for three representative unknown-bearing layer sizes under the new element-count ranges. Shown: fraction of draws whose realized unknown mass lies within +/-25% of the 0.4% target, and the 5th-95th percentile of realized mass.

| c | ego/ru-like (n=10) in-band | ego/ru-like (n=10) p5-p95 | temporal-like (n=38) in-band | temporal-like (n=38) p5-p95 | trigger-like (n=75) in-band | trigger-like (n=75) p5-p95 |
|---|---|---|---|---|---|---|
| 100 | 10.7% | 0.0004%-1.6252% | 9.8% | 0.0004%-1.6017% | 11.1% | 0.0004%-1.8175% |
| 300 | 20.8% | 0.0295%-1.0976% | 20.4% | 0.0284%-1.1708% | 22.3% | 0.0315%-1.1043% |
| 1,000 | 38.4% | 0.1350%-0.7830% | 38.6% | 0.1412%-0.7652% | 37.1% | 0.1303%-0.7631% |
| 3,000 | 62.2% | 0.2336%-0.6022% | 60.5% | 0.2323%-0.6124% | 60.8% | 0.2297%-0.6126% |
| 10,000 | 89.1% | 0.3024%-0.5107% | 88.3% | 0.3008%-0.5128% | 88.9% | 0.3024%-0.5097% |
| 20,000 | 97.4% | 0.3281%-0.4764% | 98.2% | 0.3287%-0.4710% | 97.4% | 0.3300%-0.4769% |
| 30,000 | 99.6% | 0.3422%-0.4610% | 99.5% | 0.3445%-0.4613% | 99.4% | 0.3432%-0.4610% |
| 100,000 | 100.0% | 0.3670%-0.4331% | 100.0% | 0.3672%-0.4345% | 100.0% | 0.3673%-0.4328% |

## Recommendation

Criterion: smallest c for which **>= 95% of draws land within +/-25% of the 0.4% target in every representative layer**. Result: **c = 20,000** (set as the new default `concentration_scale` in config.yaml).

Trade-off: higher c keeps the sampled vectors close to the designed rarity weights (faithful unknown rates); lower c gives more random transition behavior at the cost of large per-layer deviations from the 0.4% design target. If more transition randomness is wanted, lower c consciously and accept the wider band shown above.
