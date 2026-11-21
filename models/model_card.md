# Model card - loan default model

## What it does

Predicts the probability that a loan defaults, using what's known at application time
(customer details, credit bureau data, the loan itself and 6 months of transactions).
The probability is turned into a 0-100 risk score and a Low / Medium / High category.
It's meant as a second opinion for underwriters, not to make decisions on its own.

## Model

- Logistic Regression (C=0.01), numeric features scaled, categoricals one-hot encoded
- File: `models/default_model.pkl` (sklearn pipeline + threshold), created by `src/train.py`
- Decision threshold: 0.22 (set so that ~70% of defaulters get flagged on the train CV)

## Data

- 3,403 disbursed loans (the only ones where we know if they defaulted), 23.4% defaulted
- 80/20 split stratified on default and grouped by customer, so a customer with several
  loans isn't in both train and test
- Not used: approval_status, approved_amount, decision_date, disbursed_flag (only known after
  the decision), and names / email / phone

## Results

5-fold CV on the train set, each model at its own threshold for 70% recall:

| model | ROC-AUC | precision | recall | F1 |
|---|---|---|---|---|
| Logistic Regression | 0.739 | 0.380 | 0.706 | 0.494 |
| XGBoost | 0.732 | 0.389 | 0.702 | 0.501 |
| Random Forest | 0.727 | 0.382 | 0.705 | 0.496 |
| Decision Tree | 0.709 | 0.360 | 0.730 | 0.483 |

Test set (682 loans, only used once):

| ROC-AUC | accuracy | precision | recall | F1 |
|---|---|---|---|---|
| 0.714 | 0.641 | 0.356 | 0.656 | 0.462 |

Confusion matrix on test: 105 of 160 defaulters caught, 190 good loans wrongly flagged.

**This is below the PRD targets (ROC-AUC 0.80, recall 0.70).** Tuning, a wider XGBoost search,
log-transforming skewed columns and dropping weak features all ended up around 0.73-0.74,
so it looks like the limit of what these features can tell us.

## What drives the predictions

Ranked by mean |SHAP| (full list in `models/feature_importance.csv`):

1. debt_to_income_ratio (higher = riskier)
2. credit_score (lower = riskier)
3. num_late_payments_30d
4. interest_rate
5. loan_term_months
6. requested_amount
7. annual_income
8. credit_utilization_ratio

Interest rate and loan term come out as lower risk when higher, which is probably loan type
showing through (Personal loans: high rate, low default; Home loans: long term, high default).
Each scored customer also gets their top 3 SHAP factors in `scored_customers.top_factors`.

## Risk score

- risk_score = round(probability x 100)
- 0-19 Low, 20-34 Medium, 35-100 High

The PRD suggests 0-33 / 34-66 / 67-100, but the probabilities are realistic (average ~23%), so with
those cut offs almost nobody would be High. 20 and 35 split the CV predictions into groups that
actually default ~11%, ~28% and ~50% of the time.

Class weights weren't used because they roughly doubled the probabilities (avg 0.45 vs 0.23 real)
without improving AUC. The imbalance is handled with the lower threshold instead.

## Limitations

- The bureau snapshot is from June 2024 and the transactions are Jan-Jun 2024, so for older
  loans these were measured after the loan was given. A real model would need the data as it
  was on the application date.
- Trained only on disbursed loans. Rejected applications get scored too, but the model never
  saw how they would have turned out.
- 1,096 customers have never applied for a loan, so they don't get a score.
- `debt_to_income_ratio` is capped at 3.0 in the source data (1,793 applications).
- No fairness check yet across gender / age / region (gender isn't a feature, but other columns
  could act as proxies).
