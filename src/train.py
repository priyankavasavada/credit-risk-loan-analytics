"""Train and compare default models.

Usage: python src/train.py
"""
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from features import CATEGORICAL, NUMERIC, TARGET, make_preprocessor, modelling_data

SEED = 42


def split_data(df):
    """80/20 split, stratified on the target and grouped by customer so the
    same person never shows up in both train and test."""
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    train_idx, test_idx = next(sgkf.split(df, df[TARGET], groups=df["customer_id"]))
    return df.iloc[train_idx], df.iloc[test_idx]


def get_models():
    lr = Pipeline([
        ("prep", make_preprocessor(scale=True)),
        ("model", LogisticRegression(class_weight="balanced", max_iter=2000)),
    ])
    dt = Pipeline([
        ("prep", make_preprocessor()),
        ("model", DecisionTreeClassifier(class_weight="balanced", random_state=SEED)),
    ])
    return {
        "logistic_regression": (lr, {"model__C": [0.01, 0.1, 1, 10]}),
        "decision_tree": (dt, {"model__max_depth": [3, 4, 5, 6, 8],
                               "model__min_samples_leaf": [10, 30, 60]}),
    }


def metrics(y_true, prob, threshold=0.5):
    pred = (prob >= threshold).astype(int)
    return {
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred),
        "recall": recall_score(y_true, pred),
        "f1": f1_score(y_true, pred),
        "roc_auc": roc_auc_score(y_true, prob),
    }


def tune(pipe, grid, X, y, groups):
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    search = GridSearchCV(pipe, grid, scoring="roc_auc", cv=cv, n_jobs=-1)
    search.fit(X, y, groups=groups)
    # out-of-fold probabilities on the train set, used for metrics/confusion matrix
    oof = cross_val_predict(search.best_estimator_, X, y, groups=groups, cv=cv,
                            method="predict_proba")[:, 1]
    return search, oof


def run():
    df = modelling_data()
    train, test = split_data(df)
    X, y, groups = train[NUMERIC + CATEGORICAL], train[TARGET], train["customer_id"]
    print(f"train {len(train)} / test {len(test)}, default rate {y.mean():.3f} / {test[TARGET].mean():.3f}")

    results, fitted = [], {}
    for name, (pipe, grid) in get_models().items():
        search, oof = tune(pipe, grid, X, y, groups)
        fitted[name] = search.best_estimator_
        results.append({"model": name, **metrics(y, oof), "best_params": search.best_params_})
        print(f"\n{name}  {search.best_params_}")
        print(confusion_matrix(y, (oof >= 0.5).astype(int)))

    results = pd.DataFrame(results).set_index("model")
    print("\n5-fold CV on train set:")
    print(results.drop(columns="best_params").round(3))
    return results, fitted, train, test


if __name__ == "__main__":
    run()
