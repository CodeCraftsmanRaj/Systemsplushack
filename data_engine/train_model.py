import pandas as pd
import random
import joblib
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

# --- 1. Synthesize High-Quality Data ---
def generate_data(n=2000):
    """
    Generates a dataset with distinct keywords for L1/L2/L3 
    to ensure the model learns specific patterns.
    """
    data = []
    
    # L1: Hardware, Basic Auth, Peripherals (The "Plug it in" layer)
    l1_keywords = [
        "mouse broken", "keyboard not typing", "monitor black screen", "printer paper jam",
        "forgot password", "reset password", "login failed", "wifi icon missing",
        "headset no sound", "docking station not working", "screen flickering",
        "cannot turn on pc", "battery not charging", "cable loose"
    ]
    
    # L2: Software, Office 365, Teams, specific apps (The "Application" layer)
    l2_keywords = [
        "excel crashing", "teams microphone not working", "outlook not indexing",
        "vpn connection drop", "adobe reader error", "blue screen of death",
        "computer running slow", "install python", "license expired",
        "sharepoint access denied", "onedrive sync issue", "zoom update required",
        "sap login error", "browser cache issue"
    ]
    
    # L3: Infrastructure, Server, Network Security (The "Deep Tech" layer)
    l3_keywords = [
        "server 500 error", "firewall blocking port", "database connection refused",
        "active directory sync failure", "potential security breach",
        "switch port dead", "router config error", "api gateway timeout",
        "sql injection alert", "ssl certificate expired", "dns resolution failure",
        "subnet masking error", "virtual machine unresponsive", "aws instance down"
    ]

    for _ in range(n):
        cat = random.choice(['L1', 'L2', 'L3'])
        
        if cat == 'L1':
            base = random.choice(l1_keywords)
        elif cat == 'L2':
            base = random.choice(l2_keywords)
        else:
            base = random.choice(l3_keywords)
            
        # Add some random noise/numbers to make it realistic
        desc = f"{base} - ticket ID {random.randint(1000,9999)}"
        data.append({"Description": desc, "Support_Level": cat})
    
    return pd.DataFrame(data)

# --- 2. Train and Evaluate ---
def train_and_evaluate():
    print("--------------------------------------------------")
    print("🚀 STARTING AI MODEL TRAINING PIPELINE")
    print("--------------------------------------------------")
    
    # A. Generate Data
    print("1️⃣  Generating Synthetic Dataset (2000 records)...")
    df = generate_data()
    
    # B. Preprocessing
    print("2️⃣  Vectorizing Text (TF-IDF)...")
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    X = vectorizer.fit_transform(df['Description'])
    y = df['Support_Level']
    
    # C. Split Data (80% Train, 20% Test)
    print("3️⃣  Splitting Data (80% Train / 20% Test)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # D. Train Model
    print("4️⃣  Training Random Forest Classifier...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    # E. Evaluate
    print("5️⃣  Evaluating Performance...")
    y_pred = clf.predict(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    # --- OUTPUT RESULTS ---
    print("\n" + "="*40)
    print(f"✅ FINAL MODEL ACCURACY: {accuracy:.2%}")
    print("="*40)
    print("\n📊 DETAILED CLASSIFICATION REPORT:")
    print(report)
    
    print("\n🧩 CONFUSION MATRIX (Row=True, Col=Pred):")
    print(cm)
    
    # F. Save Model
    print("\n6️⃣  Saving Model to Disk for Edge Computing...")
    joblib.dump(clf, 'ticket_classifier.pkl')
    joblib.dump(vectorizer, 'vectorizer.pkl')
    print("   -> Saved: ticket_classifier.pkl")
    print("   -> Saved: vectorizer.pkl")

    # G. Sanity Check (Test it right now)
    print("\n🤖 SANITY CHECK (Live Test):")
    test_phrases = [
        "My printer is out of paper",           # Should be L1
        "Excel freezes when I open macros",     # Should be L2
        "The main SQL database is down"         # Should be L3
    ]
    
    for phrase in test_phrases:
        vec_phrase = vectorizer.transform([phrase])
        pred = clf.predict(vec_phrase)[0]
        print(f"   Input: '{phrase}' \t-> Prediction: {pred}")

    print("\n--------------------------------------------------")
    print("🎉 PIPELINE COMPLETE. READY FOR CLIENT APP.")
    print("--------------------------------------------------")

if __name__ == "__main__":
    train_and_evaluate()