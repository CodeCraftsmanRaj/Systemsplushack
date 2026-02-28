# client_app/ai_bridge.py
import sys
import os
import joblib
import warnings

# Suppress warnings to keep output clean
warnings.filterwarnings("ignore")

def predict_level(description):
    try:
        # Paths relative to client_app folder
        model_path = os.path.join("..", "data_engine", "ticket_classifier.pkl")
        vec_path = os.path.join("..", "data_engine", "vectorizer.pkl")
        
        if not os.path.exists(model_path):
            return "Error: Model file not found"

        # Load model (Takes ~0.5s)
        clf = joblib.load(model_path)
        vec = joblib.load(vec_path)
        
        # Predict
        vec_desc = vec.transform([description])
        prediction = clf.predict(vec_desc)[0]
        return prediction
    except Exception as e:
        return "Unknown"

if __name__ == "__main__":
    # Read argument from command line
    if len(sys.argv) > 1:
        # Join arguments in case of spaces
        desc = " ".join(sys.argv[1:])
        print(predict_level(desc))
    else:
        print("Unknown")