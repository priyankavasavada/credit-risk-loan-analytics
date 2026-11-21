# SQL insights

Notes from running `sql/analysis.sql` on the full data. All 10 queries run in under 40 ms.

**7.1 Credit score bands** - Most customers sit in Poor (580-649, 1,440) and Fair (650-699, 1,164).
Late payments jump in the bands below 650 (~2.2 avg vs ~0.4 above).

**7.2 / 7.7 Monthly approvals** - Approval rate stays around 40-50% each month. June 2024 looks
like it drops to 29% but that's because 109 of those apps are still Under Review.

**7.3 Segmentation** - Income band matters a lot more than job type. Entry income customers get
approved 20-35% of the time vs 55-80% for mid/high income. Unemployed customers are almost
never approved (4.8%).

**7.4 High-risk watchlist** - Rule-based list (score < 600, utilization > 0.8, prior defaults or
2+ 90-day lates). Will get replaced by the model risk score later.

**7.5 Default rate by loan type** - Home (31.6%) and Business (29.7%) are the worst, Personal
(20.3%) the best even though Personal has the highest interest rate.

**7.6 Loan amounts** - Home loans are the biggest (median ~69L), Gold the smallest (~4L).

**7.8 Bureau risk categories** - 992 Low, 2,268 Medium, 1,740 High using a simple score +
utilization rule.

**7.9 Transactions** - Only ~8 transactions per customer over 6 months, so these need to be
rolled up per customer before joining to loans.

**7.10 Default drivers** - Score < 600 gives a 40% default rate (vs 23% overall). Utilization
> 0.8 and prior defaults are both around 33%. DTI > 0.5 is 28.5% but covers most loans (2,340).
