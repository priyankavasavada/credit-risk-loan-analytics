# Credit Risk & Loan Approval Analytics

Credit risk project on a retail lending book (~5,000 customers, ~7,500 loan applications).
Loads the data into PostgreSQL, explores it, and builds a loan default model + a 0-100 risk score.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Put the four CSVs (`customers.csv`, `credit_history.csv`, `loan_applications.csv`, `transactions.csv`) in `datasets/`.
They aren't committed since they contain personal details.

## Structure

- `sql/` - schema and analysis queries
- `src/` - python scripts
- `notebooks/` - EDA and modelling notebooks
- `documentation/` - PRD
