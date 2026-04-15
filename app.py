import streamlit as st
import joblib
import sqlite3
import pandas as pd
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="News Portal", layout="wide", page_icon="📰")

# 2. Load Resources (Model & Database)
@st.cache_resource
def init_resources():
    # Load your trained SVM model
    model = joblib.load('svm_model.pkl')
    # Connect to SQLite database
    conn = sqlite3.connect('news_site.db', check_same_thread=False)
    cursor = conn.cursor()
    # Ensure table exists with correct schema
    cursor.execute('''CREATE TABLE IF NOT EXISTS news 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                       title TEXT, content TEXT, category TEXT, 
                       confidence REAL, date TEXT)''')
    conn.commit()
    return model, conn

model, db_conn = init_resources()
category_list = ["World", "Sports", "Business", "Sci/Tech"]
category_map = {1: "World", 2: "Sports", 3: "Business", 4: "Sci/Tech"}

# 3. Session State Management
if 'page' not in st.session_state:
    st.session_state.page = "Home"
if 'viewing_id' not in st.session_state:
    st.session_state.viewing_id = None
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- TOP NAVIGATION BAR ---
col_empty, col_home, col_admin = st.columns([8, 1, 1])
with col_home:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "Home"
        st.session_state.viewing_id = None
        st.rerun()
with col_admin:
    if st.button("👤 Admin", use_container_width=True):
        st.session_state.page = "Admin"
        st.rerun()

st.divider()

# --- ADMIN PANEL ---
if st.session_state.page == "Admin":
    # Layout for Header and Logout
    head_col, out_col = st.columns([8, 2])
    with head_col:
        st.header("🔐 Admin Upload Portal")
    
    if st.session_state.logged_in:
        with out_col:
            if st.button("Logout", type="secondary", use_container_width=True):
                st.session_state.logged_in = False
                st.rerun()

    if not st.session_state.logged_in:
        with st.columns([1, 2, 1])[1]:
            with st.form("login_form"):
                user = st.text_input("Username")
                pw = st.text_input("Password", type="password")
                if st.form_submit_button("Login", use_container_width=True):
                    if user == "admin" and pw == "admin123":
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
    else:
        tab_manual, tab_bulk = st.tabs(["Text Upload", "File Upload"])
        
        # --- MANUAL UPLOAD ---
        with tab_manual:
            with st.form("manual_form", clear_on_submit=True):
                m_title = st.text_input("News Title")
                m_content = st.text_area("News Content", height=200)
                submit = st.form_submit_button("Publish News")
                
                if submit:
                    if m_title and m_content:
                        # Prediction
                        pred = model.predict([m_content])[0]
                        cat = category_map.get(pred, "World")
                        conf = 0.95  # Simulated confidence
                        
                        # Database Entry
                        cursor = db_conn.cursor()
                        cursor.execute("INSERT INTO news (title, content, category, confidence, date) VALUES (?, ?, ?, ?, ?)",
                                       (m_title, m_content, cat, conf, datetime.now().strftime("%Y-%m-%d %H:%M")))
                        db_conn.commit()
                        
                        # IMMEDIATE FEEDBACK: Show Category and Confidence
                        st.success(f"Successfully Published!")
                        st.info(f"**Predicted Category:** {cat} | **Confidence:** {conf:.2%}")
                    else:
                        st.error("Please provide both title and content.")

        # --- BULK FILE UPLOAD ---
        with tab_bulk:
            files = st.file_uploader("Upload .txt files", type=['txt'], accept_multiple_files=True)
            if st.button("Process & Publish All") and files:
                cursor = db_conn.cursor()
                for f in files:
                    content = f.read().decode("utf-8")
                    title = f.name.replace(".txt", "")
                    
                    # Prediction
                    pred = model.predict([content])[0]
                    cat = category_map.get(pred, "World")
                    conf = 0.89
                    
                    cursor.execute("INSERT INTO news (title, content, category, confidence, date) VALUES (?, ?, ?, ?, ?)",
                                   (title, content, cat, conf, datetime.now().strftime("%Y-%m-%d %H:%M")))
                    
                    # Show result for each file immediately
                    st.write(f"📄 **{title}** classified as **{cat}** ({conf:.2%} confidence)")
                
                db_conn.commit()
                st.success(f"Published {len(files)} articles successfully.")

# --- PUBLIC NEWS SITE ---
else:
    # ARTICLE DETAIL VIEW
    if st.session_state.viewing_id:
        cursor = db_conn.cursor()
        cursor.execute("SELECT * FROM news WHERE id=?", (st.session_state.viewing_id,))
        article = cursor.fetchone()
        
        if article:
            if st.button("← Back to Feed"):
                st.session_state.viewing_id = None
                st.rerun()
            st.title(article[1])
            st.caption(f"📅 Published: {article[5]} | 🏷️ Category: {article[3]}")
            st.markdown("---")
            st.write(article[2])
        else:
            st.error("Article not found.")
            st.session_state.viewing_id = None

    # LIST VIEW (HOME)
    else:
        st.title("🌐 Latest News")
        tabs = st.tabs(["All News"] + category_list)
        
        def render_news_cards(query, tab_id):
            df = pd.read_sql(query, db_conn)
            if df.empty:
                st.info("No news articles found in this category.")
            else:
                for _, row in df.iterrows():
                    with st.container(border=True):
                        col_txt, col_btn = st.columns([5, 1])
                        with col_txt:
                            st.subheader(row['title'])
                            st.caption(f"CATEGORY: {row['category'].upper()} | 📅 {row['date']}")
                            st.write(row['content'][:150] + "...")
                        with col_btn:
                            st.write(" ")
                            if st.button("Read More", key=f"btn_{tab_id}_{row['id']}", use_container_width=True):
                                st.session_state.viewing_id = row['id']
                                st.rerun()

        with tabs[0]:
            render_news_cards("SELECT * FROM news ORDER BY id DESC", "all")
            
        for i, cat_name in enumerate(category_list):
            with tabs[i+1]:
                render_news_cards(f"SELECT * FROM news WHERE category = '{cat_name}' ORDER BY id DESC", cat_name.lower())
