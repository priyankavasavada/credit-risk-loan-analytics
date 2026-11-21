# scores every loan application with the saved model and writes the latest
# score per customer to the scored_customers table
# run from the project folder: python src/risk_score.py
import joblib
import numpy as np
import pandas as pd
import shap

from features import cat_cols, engine, get_data, num_cols

saved = joblib.load("models/default_model.pkl")
model, threshold = saved["model"], saved["threshold"]

df = get_data()
X = df[num_cols + cat_cols]
status = pd.read_sql("SELECT application_id, approval_status FROM loan_applications", engine)
df = df.merge(status, on="application_id")

df["default_probability"] = model.predict_proba(X)[:, 1].round(4)
df["risk_score"] = (df["default_probability"] * 100).round().astype(int)
# bands picked from the CV results: actual default rate is ~11% / ~28% / ~50%
df["risk_category"] = pd.cut(df["risk_score"], [-1, 19, 34, 100], labels=["Low Risk", "Medium Risk", "High Risk"])
df["predicted_default"] = (df["default_probability"] >= threshold).astype(int)

# top 3 features pushing each score up
Xt = model["prep"].transform(X)
explainer = shap.Explainer(model["model"], shap.maskers.Independent(Xt, max_samples=len(Xt)))
shap_values = explainer(Xt).values
names = [n.split("__")[1] for n in model["prep"].get_feature_names_out()]
top = np.argsort(-shap_values, axis=1)[:, :3]
df["top_factors"] = [", ".join(names[i] for i in row) for row in top]

# one row per customer, using their most recent application
scored = (df.sort_values("application_date")
            .groupby("customer_id").tail(1)
            [["customer_id", "application_id", "application_date", "loan_type", "approval_status", "default_probability",
              "risk_score", "risk_category", "predicted_default", "top_factors"]])
scored["risk_category"] = scored["risk_category"].astype(str)

scored.to_sql("scored_customers", engine, if_exists="replace", index=False)
print(len(scored), "customers scored")
print(scored["risk_category"].value_counts())
