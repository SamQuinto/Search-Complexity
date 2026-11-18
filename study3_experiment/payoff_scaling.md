# Payoff scaling

Each multiplier applies to all nine Include scores for that role. Each feature score is then rounded to two decimal places using ordinary nearest rounding. Exclude scores and reservation values are zero. The Hard coordinator multiplier is 1.428954129606, a small adjustment before rounding that maintains the £1 minimum and £11.25 maximum.

The largest individual payoff among the four agreements is £11.25 in both conditions. Every agreement pays every role at least £1. The lowest payoff is £1.15 in Easy and £1.00 in Hard.

| Condition | Role | Multiplier | Lowest agreement payoff | Highest agreement payoff | Average over four agreements |
| --- | --- | ---: | ---: | ---: | ---: |
| Easy | Writer (A) | 1.24861265260821 | £1.17 | £11.25 | £4.44 |
| Easy | Coordinator (B) | 1.32979642720005 | £1.15 | £10.41 | £4.90 |
| Easy | Trainer (C) | 1.70940759179676 | £1.67 | £10.02 | £4.91 |
| Hard | Writer (A) | 1.31895375497592 | £3.90 | £5.05 | £4.47 |
| Hard | Coordinator (B) | 1.428954129606 | £1.00 | £11.25 | £5.32 |
| Hard | Trainer (C) | 0.991227031609748 | £1.14 | £8.92 | £4.47 |

The multipliers apply to the two-decimal point tables in commit ea355bfed541bd0bf4660a6a2e7b805ff44fe215. The selected table IDs end in 4a93c0a77674 for Easy and 61024eb53d22 for Hard.

All 512 offers were checked after rounding. The same people accept each offer, and both conditions keep the same four agreements. Easy has 91 reachable starting offers and 421 without an improving path. Hard has 68 and 444. Search complexity is 82.23% in Easy and 86.72% in Hard.

The earlier checks of identical simulated offer histories used full-precision scaled scores. Rounding can change ties and rankings among offers even when acceptance decisions are identical.
