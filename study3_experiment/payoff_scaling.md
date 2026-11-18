# Payoff scaling

The highest individual payoff among the four agreements is £11.25 in both conditions. Every agreement gives every role at least £1. The average over the four agreements is approximately £4.75 per person in each condition, giving each possible agreement equal weight.

Each multiplier applies to all nine Include scores for that role. Feature scores retain the precision of the multiplication. Round the final payment to two decimal places. Exclude scores and reservation values are zero.

| Condition | Role | Multiplier | Lowest agreement payoff | Highest agreement payoff | Average over four agreements |
| --- | --- | ---: | ---: | ---: | ---: |
| Easy | Writer (A) | 1.24861265260821 | £1.16 | £11.25 | £4.43 |
| Easy | Coordinator (B) | 1.32979642720005 | £1.16 | £10.41 | £4.91 |
| Easy | Trainer (C) | 1.70940759179676 | £1.68 | £10.02 | £4.91 |
| Hard | Writer (A) | 1.31895375497592 | £3.90 | £5.05 | £4.47 |
| Hard | Coordinator (B) | 1.4294790343075 | £1.00 | £11.25 | £5.31 |
| Hard | Trainer (C) | 0.991227031609748 | £1.14 | £8.92 | £4.47 |

The multipliers apply to the two-decimal point tables in commit ea355bfed541bd0bf4660a6a2e7b805ff44fe215. The selected table IDs end in 4a93c0a77674 for Easy and 61024eb53d22 for Hard.

All 512 offers were checked. Individual acceptance decisions and offer rankings are retained. Both conditions keep four agreements. Easy has 91 reachable starting offers and 421 without an improving path. Hard has 68 and 444. With the same recorded seeds, all 2,700 model runs per condition reproduced identical offer histories and agreement outcomes.
