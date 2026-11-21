import pandas as pd
from sqlalchemy import create_engine
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

engine = create_engine("postgresql+psycopg2:///credit_risk")

num_cols = [
    "age", "dependents", "years_at_residence", "annual_income", "tenure_years",
    "credit_score", "num_open_accounts", "num_credit_inquiries_6m", "credit_utilization_ratio",
    "num_late_payments_30d", "num_late_payments_90d", "num_defaults_prior", "bankruptcies",
    "oldest_account_age_months", "debt_to_limit",
    "requested_amount", "loan_term_months", "interest_rate", "debt_to_income_ratio",
    "loan_to_income", "collateral_flag",
    "total_inflow", "total_outflow", "net_cash_flow", "emi_outflow", "avg_balance",
    "txn_count", "inflow_outflow_ratio",
]
cat_cols = ["loan_type", "employment_type", "education", "residence_type", "marital_status"]


def get_data():
    customers = pd.read_sql("SELECT * FROM customers", engine)
    customers = customers.drop(columns=["first_name", "last_name", "email", "phone"])
    credit = pd.read_sql("SELECT * FROM credit_history", engine)
    loans = pd.read_sql("SELECT * FROM loan_applications", engine)
    txns = pd.read_sql("SELECT * FROM transactions", engine)

    # one row per customer for transactions
    txns["inflow"] = txns["amount"].where(txns["transaction_type"] == "Credit", 0)
    txns["outflow"] = txns["amount"].where(txns["transaction_type"] == "Debit", 0)
    txns["emi"] = txns["amount"].where(txns["category"] == "EMI", 0)
    txn = txns.groupby("customer_id").agg(
        total_inflow=("inflow", "sum"),
        total_outflow=("outflow", "sum"),
        emi_outflow=("emi", "sum"),
        avg_balance=("balance_after", "mean"),
        txn_count=("transaction_id", "count"),
    ).reset_index()
    txn["net_cash_flow"] = txn["total_inflow"] - txn["total_outflow"]
    txn["inflow_outflow_ratio"] = txn["total_inflow"] / (txn["total_outflow"] + 1)

    # these are only known after the decision so they can't be features
    loans = loans.drop(columns=["approval_status", "approved_amount", "decision_date", "disbursed_flag"])

    df = loans.merge(customers, on="customer_id").merge(credit, on="customer_id").merge(txn, on="customer_id")

    days = pd.to_datetime(df["application_date"]) - pd.to_datetime(df["customer_since"])
    df["tenure_years"] = (days.dt.days / 365).clip(lower=0)  # some loans are dated before customer_since
    df["debt_to_limit"] = df["total_outstanding_debt"] / df["total_credit_limit"]
    df["loan_to_income"] = df["requested_amount"] / df["annual_income"]
    df[cat_cols] = df[cat_cols].fillna("Unknown")

    return df


def preprocessor(scale=False):
    num = make_pipeline(SimpleImputer(strategy="median"), StandardScaler() if scale else "passthrough")
    return ColumnTransformer([
        ("num", num, num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
    ])
