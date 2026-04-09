"""
Isolation Forest Training Script

Trains an Isolation Forest model on realistic SPPU marksheet feature vectors.
Generates synthetic "authentic" data points based on typical SPPU grading patterns.

Usage:
    cd backend
    python training/train_isolation_forest.py
"""

import os
import sys

import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    import joblib
except ImportError:
    print("scikit-learn and joblib are required: pip install scikit-learn joblib")
    sys.exit(1)


MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml_models")
MODEL_PATH = os.path.join(MODEL_DIR, "isolation_forest.pkl")


def generate_authentic_data(n_samples: int = 200) -> np.ndarray:
    """
    Generate synthetic feature vectors representing authentic SPPU marksheets.

    Features:
    1. SGPA (typically 4.0 - 9.5)
    2. Mean total marks (typically 60 - 130 out of 150)
    3. Std dev of marks (typically 5 - 25)
    4. Number of subjects (typically 5 - 8)
    5. Mean internal/external ratio (typically 0.3 - 0.8)
    6. Max total marks (typically 80 - 145)
    7. Min total marks (typically 40 - 100)
    """
    np.random.seed(42)

    data = []
    for _ in range(n_samples):
        num_subjects = np.random.choice([5, 6, 7, 8])

        # Generate realistic marks per subject
        # Base performance level for this student
        base_perf = np.random.uniform(40, 135)
        totals = np.clip(
            base_perf + np.random.normal(0, 15, num_subjects),
            20, 148
        )

        mean_marks = np.mean(totals)
        std_marks = np.std(totals)
        max_marks = np.max(totals)
        min_marks = np.min(totals)

        # Internal/external ratio (internal is typically 30-50 out of 50, external 20-100 out of 100)
        ratio = np.random.uniform(0.3, 0.8)

        # SGPA derived from marks (roughly percentage/10 with some noise)
        percentage = mean_marks / 150 * 100
        sgpa = np.clip(percentage / 10 * np.random.uniform(0.95, 1.05), 0, 10)
        sgpa = round(sgpa, 2)

        features = [
            sgpa,
            mean_marks,
            std_marks,
            float(num_subjects),
            ratio,
            max_marks,
            min_marks,
        ]
        data.append(features)

    return np.array(data)


def main():
    print("=" * 60)
    print("Isolation Forest Training — SPPU Marksheet Anomaly Detector")
    print("=" * 60)

    # Generate training data
    data = generate_authentic_data(200)
    print(f"\nGenerated {len(data)} authentic data points")
    print(f"Feature shape: {data.shape}")
    print(f"\nFeature ranges:")
    feature_names = ["SGPA", "Mean marks", "Std marks", "Num subjects",
                     "Int/Ext ratio", "Max marks", "Min marks"]
    for i, name in enumerate(feature_names):
        print(f"  {name}: {data[:, i].min():.2f} - {data[:, i].max():.2f} (mean: {data[:, i].mean():.2f})")

    # Train Isolation Forest
    print(f"\nTraining Isolation Forest...")
    model = IsolationForest(
        n_estimators=100,
        contamination=0.1,  # expect ~10% anomalies
        max_samples="auto",
        random_state=42,
    )
    model.fit(data)

    # Test with authentic and anomalous samples
    print("\n--- Test Predictions ---")

    # Normal sample
    normal = np.array([[7.5, 95.0, 12.0, 6.0, 0.5, 120.0, 70.0]])
    score_normal = model.decision_function(normal)[0]
    pred_normal = model.predict(normal)[0]
    print(f"Normal student (SGPA=7.5):  score={score_normal:.4f}, prediction={'normal' if pred_normal == 1 else 'ANOMALY'}")

    # Suspicious: perfect scores everywhere
    suspicious1 = np.array([[10.0, 150.0, 0.0, 6.0, 0.5, 150.0, 150.0]])
    score_s1 = model.decision_function(suspicious1)[0]
    pred_s1 = model.predict(suspicious1)[0]
    print(f"Perfect marks (SGPA=10):    score={score_s1:.4f}, prediction={'normal' if pred_s1 == 1 else 'ANOMALY'}")

    # Suspicious: impossible SGPA
    suspicious2 = np.array([[9.9, 50.0, 5.0, 6.0, 0.5, 55.0, 45.0]])
    score_s2 = model.decision_function(suspicious2)[0]
    pred_s2 = model.predict(suspicious2)[0]
    print(f"Low marks but high SGPA:    score={score_s2:.4f}, prediction={'normal' if pred_s2 == 1 else 'ANOMALY'}")

    # Suspicious: 1 subject only
    suspicious3 = np.array([[8.0, 100.0, 0.0, 1.0, 0.5, 100.0, 100.0]])
    score_s3 = model.decision_function(suspicious3)[0]
    pred_s3 = model.predict(suspicious3)[0]
    print(f"Only 1 subject:             score={score_s3:.4f}, prediction={'normal' if pred_s3 == 1 else 'ANOMALY'}")

    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved to: {MODEL_PATH}")
    print(f"Model file size: {os.path.getsize(MODEL_PATH) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
