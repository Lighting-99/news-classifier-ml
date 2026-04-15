import streamlit as st
import joblib
import sqlite3
import pandas as pd
from datetime import datetime

# --- CONFIG & MODEL LOAD ---
st.set_page_config(page_title="Global News Portal", layout="wide")

@st.cache_resource
def load_resources():
    model = joblib.load('svm_model.pkl')
    conn = sqlite3.connect('news_db.sqlite', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS news 
                      (id INTEGER PRIMARY KEY, title TEXT, content TEXT, 
                       category TEXT, confidence REAL, date TEXT)''')
    conn.commit()
    return model, conn

model, db_conn = load_resources()
categories = ["Home", "World", "Sports", "Business", "Sci/Tech"]
category_map = {1: "World", 2: "Sports", 3: "Business", 4: "Sci/Tech"}

# --- AUTHENTICATION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'viewing_article' not in st.session_state:
    st.session_state.viewing_article = None

# --- SIDEBAR NAV ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["News Site", "Admin Portal"])

# --- ADMIN PORTAL ---
if page == "Admin Portal":
    st.header("🔐 Admin Dashboard")
    
    if not st.session_state.logged_in:
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Login"):
            if user == "admin" and pw == "password123": # Change this!
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials")
    else:
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

        st.subheader("Upload News")
        upload_type = st.radio("Upload via", ["Manual Text", "Multiple Text Files"])
        
        news_to_process = []

        if upload_type == "Manual Text":
            title = st.text_input("News Title")
            body = st.text_area("Content")
            if st.button("Publish"):
                news_to_process.append({"title": title, "body": body})
        
        else:
            files = st.file_uploader("Upload .txt files", type=['txt'], accept_multiple_files=True)
            if st.button("Process & Publish Files") and files:
                for f in files:
                    content = f.read().decode("utf-8")
                    news_to_process.append({"title": f.name.replace(".txt", ""), "body": content})

        # Process news through ML model
        for item in news_to_process:
            # Predict
            pred = model.predict([item['body']])[0]
            label = category_map.get(pred, "World")
            
            # Confidence (Mock-up: SVM decision score)
            conf = 0.92 # SVM doesn't give direct prob unless trained specially
            
            # Save to DB
            cur = db_conn.cursor()
            cur.execute("INSERT INTO news (title, content, category, confidence, date) VALUES (?, ?, ?, ?, ?)",
                        (item['title'], item['body'], label, conf, datetime.now().strftime("%Y-%m-%d %H:%M")))
            db_conn.commit()
            st.success(f"Published: {item['title']} as {label}")

# --- NEWS SITE ---
else:
    # Article Detail View
    if st.session_state.viewing_article:
        article = st.session_state.viewing_article
        if st.button("← Back to Feed"):
            st.session_state.viewing_article = None
            st.rerun()
        
        st.title(article[1])
        st.caption(f"{article[3]} | Published: {article[5]}")
        st.write(article[2])
    
    # List View
    else:
        st.title("🌐 Global News Portal")
        tabs = st.tabs(categories)
        
        for i, tab in enumerate(tabs):
            with tab:
                query = "SELECT * FROM news ORDER BY id DESC"
                if categories[i] != "Home":
                    query = f"SELECT * FROM news WHERE category = '{categories[i]}' ORDER BY id DESC"
                
                df = pd.read_sql(query, db_conn)
                
                if df.empty:
                    st.write("No news available in this category.")
                else:
                    for index, row in df.iterrows():
                        with st.container(border=True):
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.subheader(row['title'])
                                st.write(row['content'][:150] + "...")
                                if st.button("Read More", key=f"btn_{row['id']}"):
                                    st.session_state.viewing_article = row
                                    st.rerun()
                            with col2:
                                st.markdown(f"**{row['category']}**")
                                st.caption(f"Score: {row['confidence']:.2%}")
