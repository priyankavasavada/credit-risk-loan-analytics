# Credit Risk & Loan Approval Analytics

## What this project is about

Credora Finance is a (fictional) retail lender that gives out personal, home, auto, education,
business and gold loans across 20 Indian cities. Right now their loan decisions mostly rely on a
single credit score and the underwriter's judgement, so approvals are inconsistent, nobody has a
forward-looking estimate of who will default, and there's no single view of how risky the portfolio is.

The data covers about 5,000 customers and 7,500 loan applications from Jul 2022 to Jun 2024.
46% of decided applications were approved, and 23% of the loans that were given out defaulted.

## What we're doing here

1. **Put all the data in one place** - the customer, credit bureau, loan application and transaction
   CSVs are loaded into PostgreSQL with proper keys and constraints, so everything can be joined on `customer_id`.
2. **Analyse it with SQL** - 10 queries answering the main risk questions (approval trends, default
   rate by loan type, segmentation, high-risk customers, what drives defaults).
3. **Clean and explore** - check data quality, then look at what separates loans that defaulted from ones that didn't.
4. **Predict default** - train Logistic Regression, Decision Tree, Random Forest and XGBoost on the
   disbursed loans and pick the best one.
5. **Score every customer** - turn the model's probability into a 0-100 risk score with a
   Low / Medium / High label, plus the top 3 reasons behind each score.
6. **Dashboard** - a Streamlit dashboard for underwriters and risk managers showing approval and default
   trends, the risk mix, geography, a high-risk watchlist and a customer lookup.

The model doesn't replace the underwriter, it gives them a second opinion backed by data.

## Results

- Logistic Regression ended up the best model: ROC-AUC 0.74 in cross validation, 0.71 on the test set,
  catching ~66-70% of defaulters. That's below the 0.80 target in the PRD, nothing I tried got past ~0.74.
- Biggest drivers of default: debt-to-income ratio, credit score and 30-day late payments.
- Risk bands: Low (0-19), Medium (20-34), High (35-100), which default about 11%, 28% and 50% of the time.

More detail in `models/model_card.md` and `documentation/sql_insights.md`.

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
python src/data_load.py                  # create tables + load csvs
psql -d credit_risk -f sql/analysis.sql  # the 10 analysis queries
python src/train.py                      # train and compare models, saves models/default_model.pkl
python src/risk_score.py                 # scores customers into the scored_customers table
streamlit run dashboard/app.py           # dashboard
```

Notebooks in `notebooks/` go in order 00 to 04.

## Structure

- `sql/` - schema and analysis queries
- `src/` - python scripts
- `notebooks/` - cleaning, EDA, features, modelling, risk scoring
- `models/` - saved model, results, feature importance, model card
- `dashboard/` - streamlit app
- `documentation/` - PRD and SQL notes
