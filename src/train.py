from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.tree import DecisionTreeClassifier

from features import cat_cols, get_data, num_cols, preprocessor

df = get_data()
df = df[df["loan_default"].notna()]

X = df[num_cols + cat_cols]
y = df["loan_default"].astype(int)

# 80/20 split, grouped by customer so the same person isn't in both train and test
cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
train_idx, test_idx = next(cv.split(X, y, groups=df["customer_id"]))
X_train, y_train = X.iloc[train_idx], y.iloc[train_idx]
groups = df["customer_id"].iloc[train_idx]

models = {
    "logistic_regression": (
        Pipeline([("prep", preprocessor(scale=True)),
                  ("model", LogisticRegression(class_weight="balanced", max_iter=2000))]),
        {"model__C": [0.01, 0.1, 1, 10]},
    ),
    "decision_tree": (
        Pipeline([("prep", preprocessor()),
                  ("model", DecisionTreeClassifier(class_weight="balanced", random_state=42))]),
        {"model__max_depth": [3, 4, 5, 6, 8], "model__min_samples_leaf": [10, 30, 60]},
    ),
}

if __name__ == "__main__":
    for name, (pipe, params) in models.items():
        grid = GridSearchCV(pipe, params, scoring="roc_auc", cv=cv)
        grid.fit(X_train, y_train, groups=groups)

        # cross validated predictions on the train set, test set is kept for the final model
        prob = cross_val_predict(grid.best_estimator_, X_train, y_train, groups=groups,
                                 cv=cv, method="predict_proba")[:, 1]
        pred = (prob >= 0.5).astype(int)

        print(name, grid.best_params_)
        print("ROC-AUC:", round(roc_auc_score(y_train, prob), 3))
        print(confusion_matrix(y_train, pred))
        print(classification_report(y_train, pred, digits=3))
