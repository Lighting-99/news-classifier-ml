import streamlit as st
import joblib
import io

# 1. Page Configuration
st.set_page_config(page_title="News Classifier ML", layout="centered", page_icon="📰")

# 2. Load the SVM Model (The only one we need now)
@st.cache_resource
def load_svm_model():
    try:
        # We only load the SVM model
        model = joblib.load('svm_model.pkl')
        return model
    except FileNotFoundError:
        return None

svm_model = load_svm_model()
category_map = {1: "World", 2: "Sports", 3: "Business", 4: "Sci/Tech"}

# --- UI Header ---
st.title("📰 News Classification")

if svm_model is None:
    st.error("⚠️ 'svm_model.pkl' not found! Please run your training script first.")
    st.stop()

# --- Tabs Implementation ---
tab1, tab2 = st.tabs(["Predict by Text", "Predict by File"])

# --- TAB 1: PREDICT BY TEXT ---
with tab1:
    news_input = st.text_area(
        label="Paste news article content here...",
        placeholder="Type or paste the news text you want to classify...",
        height=250,
        key="text_input"
    )

    if st.button("Classify News", type="primary", use_container_width=True):
        if not news_input.strip():
            st.warning("Please enter some news text first.")
        else:
            # Prediction happens silently using SVM
            prediction = svm_model.predict([news_input])[0]
            label = category_map.get(prediction, "Unknown")
            
            st.markdown("---")
            st.subheader(f"Result: :blue[{label}]")

# --- TAB 2: PREDICT BY FILE ---
with tab2:
    uploaded_file = st.file_uploader("Upload your news file (.txt)", type=['txt'])
    
    if st.button("Classify File", type="primary", use_container_width=True):
        if uploaded_file is None:
            st.error("Please upload a .txt file first!")
        else:
            # Read and decode
            raw_text = uploaded_file.read().decode("utf-8")
            
            if not raw_text.strip():
                st.error("The uploaded file is empty.")
            else:
                with st.expander("Show uploaded text content"):
                    st.write(raw_text)

                # Prediction happens silently using SVM
                prediction = svm_model.predict([raw_text])[0]
                label = category_map.get(prediction, "Unknown")
                
                st.markdown("---")
                st.subheader(f"Result: :green[{label}]")
