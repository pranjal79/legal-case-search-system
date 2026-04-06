import mlflow
import os

# MLflow tracking setup
MLFLOW_TRACKING_URI = "file:./mlflow/mlruns"
EXPERIMENT_NAME = "legal-case-search"

def setup_mlflow():
    """
    Initialize MLflow tracking
    """
    # Set tracking URI
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    # Create or get experiment
    try:
        experiment_id = mlflow.create_experiment(
            EXPERIMENT_NAME,
            artifact_location="./mlflow/artifacts"
        )
    except Exception as e:
        # Experiment already exists
        experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
        experiment_id = experiment.experiment_id
    
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    print(f"✅ MLflow initialized")
    print(f"   Experiment: {EXPERIMENT_NAME}")
    print(f"   Tracking URI: {MLFLOW_TRACKING_URI}")
    print(f"   Experiment ID: {experiment_id}")
    
    return experiment_id

if __name__ == "__main__":
    setup_mlflow()