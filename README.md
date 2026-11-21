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

## Running it

Needs a postgres database called `credit_risk` (`createdb credit_risk`). On a Mac xgboost also needs `brew install libomp`.

```bash
python src/data_load.py    # create tables + load csvs
python src/train.py        # train and compare models, saves models/default_model.pkl
python src/risk_score.py   # scores customers into the scored_customers table
```

Notebooks in `notebooks/` go in order 00 to 04.

## Results

Logistic Regression ended up the best model: ROC-AUC 0.74 in cross validation, 0.71 on the test set,
catching ~66-70% of defaulters. Details in `models/model_card.md`.

## Structure

- `sql/` - schema and analysis queries
- `src/` - python scripts
- `notebooks/` - cleaning, EDA, features, modelling, risk scoring
- `models/` - saved model, results, feature importance, model card
- `documentation/` - PRD
