import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from features import cat_cols, get_data, num_cols, preprocessor

df = get_data()
df = df[df["loan_default"].notna()]

X = df[num_cols + cat_cols]
y = df["loan_default"].astype(int)

# 80/20 split, grouped by customer so the same person isn't in both train and test
cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
train_idx, test_idx = next(cv.split(X, y, groups=df["customer_id"]))
X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
X_test, y_test = X.iloc[test_idx], y.iloc[test_idx]
groups = df["customer_id"].iloc[train_idx]

# no class weights here so the probabilities stay realistic (~23% average),
# the imbalance is handled by lowering the threshold instead
models = {
    "logistic_regression": (
        Pipeline([("prep", preprocessor(scale=True)),
                  ("model", LogisticRegression(max_iter=2000))]),
        {"model__C": [0.01, 0.1, 1, 10]},
    ),
    "decision_tree": (
        Pipeline([("prep", preprocessor()),
                  ("model", DecisionTreeClassifier(random_state=42))]),
        {"model__max_depth": [3, 4, 5, 6, 8], "model__min_samples_leaf": [10, 30, 60]},
    ),
    "random_forest": (
        Pipeline([("prep", preprocessor()),
                  ("model", RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1))]),
        {"model__max_depth": [6, 10, None], "model__min_samples_leaf": [5, 20, 50],
         "model__max_features": ["sqrt", 0.3]},
    ),
    "xgboost": (
        Pipeline([("prep", preprocessor()),
                  ("model", XGBClassifier(subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1))]),
        {"model__n_estimators": [200, 400], "model__max_depth": [2, 3, 4],
         "model__learning_rate": [0.03, 0.1]},
    ),
}


def find_threshold(y_true, prob, target_recall=0.70):
    # highest threshold that still catches 70% of the defaulters
    threshold = 0.5
    while recall_score(y_true, prob >= threshold) < target_recall:
        threshold -= 0.01
    return round(threshold, 2)


def scores(y_true, prob, threshold=0.5):
    pred = (prob >= threshold).astype(int)
    return {"accuracy": accuracy_score(y_true, pred), "precision": precision_score(y_true, pred),
            "recall": recall_score(y_true, pred), "f1": f1_score(y_true, pred),
            "roc_auc": roc_auc_score(y_true, prob)}


if __name__ == "__main__":
    results, fitted = {}, {}
    for name, (pipe, params) in models.items():
        grid = GridSearchCV(pipe, params, scoring="roc_auc", cv=cv, n_jobs=-1)
        grid.fit(X_train, y_train, groups=groups)
        prob = cross_val_predict(grid.best_estimator_, X_train, y_train, groups=groups,
                                 cv=cv, method="predict_proba")[:, 1]
        threshold = find_threshold(y_train, prob)
        results[name] = {"threshold": threshold, **scores(y_train, prob, threshold)}
        fitted[name] = (grid.best_estimator_, prob)
        print(name, grid.best_params_)

    results = pd.DataFrame(results).T.round(3)
    print("\n5-fold CV on train set, threshold set for 70% recall")
    print(results)
    results.to_csv("models/cv_results.csv")

    best = results["roc_auc"].idxmax()
    model, prob = fitted[best]
    threshold = results.loc[best, "threshold"]

    # test set is only used here, once
    test_prob = model.predict_proba(X_test)[:, 1]
    print(f"\nbest model: {best}, threshold {threshold}")
    print("test set:", {k: round(v, 3) for k, v in scores(y_test, test_prob, threshold).items()})
    print(confusion_matrix(y_test, test_prob >= threshold))

    joblib.dump({"model": model, "threshold": threshold, "name": best}, "models/default_model.pkl")
