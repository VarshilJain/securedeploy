"""
Model training pipeline for Financial News Sentiment Classifier.
Uses TF-IDF Vectorization and Logistic Regression.
Educational demonstration dataset: not for actual financial trading decisions.
"""

import argparse
import os
import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
import joblib

DEFAULT_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "headlines.csv")
DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")


def build_pipeline() -> Pipeline:
    """Constructs a deterministic NLP pipeline."""
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    max_features=1500,
                    stop_words="english",
                    lowercase=True,
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    C=1.0,
                    solver="lbfgs",
                    random_state=42,
                    max_iter=1000,
                ),
            ),
        ]
    )


def train_model(
    data_path: str = DEFAULT_DATA_PATH,
    model_path: str = DEFAULT_MODEL_PATH,
    random_state: int = 42,
):
    """Loads dataset, trains pipeline deterministically, prints metrics, and saves model."""
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at: {data_path}")

    print(f"[*] Loading training dataset from: {data_path}")
    df = pd.read_csv(data_path)

    # Validate dataset structure
    if "headline" not in df.columns or "label" not in df.columns:
        raise ValueError("Dataset must contain 'headline' and 'label' columns.")

    df["headline"] = df["headline"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip().str.lower()
    df = df[df["headline"].str.len() > 0]

    print(f"[*] Total valid headlines loaded: {len(df)}")
    print(f"[*] Class distribution:\n{df['label'].value_counts().to_string()}")

    x_train, x_test, y_train, y_test = train_test_split(
        df["headline"],
        df["label"],
        test_size=0.2,
        random_state=random_state,
        stratify=df["label"],
    )

    pipeline = build_pipeline()
    print("[*] Training TF-IDF + Logistic Regression model...")
    pipeline.fit(x_train, y_train)

    # Evaluate on held-out test split
    y_pred = pipeline.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, digits=4)

    print("\n" + "=" * 50)
    print(f"[*] Test Accuracy: {accuracy * 100:.2f}%")
    print("=" * 50)
    print("[*] Classification Report:\n")
    print(report)
    print("=" * 50)

    # Save artifact
    output_dir = os.path.dirname(os.path.abspath(model_path))
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    joblib.dump(pipeline, model_path)
    print(f"[*] Model successfully serialized to: {model_path}\n")

    return pipeline, accuracy


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Sentiment Classifier")
    parser.add_argument(
        "--data", default=DEFAULT_DATA_PATH, help="Path to input headlines.csv"
    )
    parser.add_argument(
        "--output", default=DEFAULT_MODEL_PATH, help="Output path for model.joblib"
    )
    args = parser.parse_args()

    try:
        train_model(data_path=args.data, model_path=args.output)
    except Exception as exc:
        print(f"[!] Training failed: {exc}", file=sys.stderr)
        sys.exit(1)
