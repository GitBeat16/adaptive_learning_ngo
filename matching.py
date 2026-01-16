import streamlit as st
import time
import os
import json
import sqlite3
import requests
from database import DB_PATH
from ai_helper import ask_ai
from streamlit_lottie import st_lottie

# Ensure upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# THREAD-SAFE DATABASE HELPER
# =========================================================
def get_db_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def run_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    """Execution wrapper to prevent Threading and Operational Errors."""
    conn = get_db_connection()
    try:
        # Enable dictionary-like access to avoid index errors
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        cursor.execute(query, params)
        if commit:
            conn.commit()
        if fetchone:
            res = cursor.fetchone()
            return dict(res) if res else None
        if fetchall:
            res = cursor.fetchall()
            return [dict(row) for row in res] if res else []
    except sqlite3.OperationalError as e:
        st.error(f"Database Configuration Error: {e}")
        return None
    finally:
        conn.close()

# =========================================================
# ASSETS & UI
# =========================================================
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        return r.json() if r.status_code == 200 else None
    except:
        return None

def inject_emerald_theme():
    st.markdown("""
        <style>
        .stApp { background-color: #f0fdf4; }
        .emerald-card {
            background: white !important;
            padding: 30px !important;
            border-radius: 20px !important;
            border-top: 10px solid #059669 !important;
            box-shadow: 0 10px 25px rgba(5, 150, 105, 0.1) !important;
            margin-bottom: 25px;
            color: #064e3b;
        }
        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            height: 3em;
            width: 100%;
        }
        .chat-scroll { background: #ecfdf5 !important; border: 1px solid #d1fae5 !important; border-radius: 12px; padding: 15px; height: 350px; overflow-y: auto; margin-bottom: 20px; }
        .bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 10px; max-width: 80%; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #064e3b; border: 1px solid #d1fae5; border-bottom-left-radius: 2px; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# PAGE MODULES
# =========================================================

def show_discovery():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Network Discovery")
    lottie_data = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_6p8ov98e.json")
    if lottie_data: st_lottie(lottie_data, height=200)
    st.write("Scanning for compatible nodes...")
    
    if st.button("Initiate Scan"):
        peer = run_query("""
            SELECT p.user_id, a.name FROM profiles p 
            JOIN auth_users a ON a.id = p.user_id 
            WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,), fetchone=True)
        
        if peer:
            m_id = f"sess_{int(time.time())}"
            st.session_state.peer_info = {"id": peer['user_id'], "name": peer['name']}
            st.session_state.current_match_id = m_id
            run_query("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, st.session_state.user_id), commit=True)
            run_query("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, peer['user_id']), commit=True)
            st.session_state.session_step = "confirmation"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Connection Request")
    status_data = run_query("SELECT accepted FROM profiles WHERE user_id=?", (st.session_state.user_id,), fetchone=True)
    peer_data = run_query("SELECT accepted FROM profiles WHERE user_id=?", (st.session_state.peer_info['id'],), fetchone=True)
    my_acc = status_data['accepted'] if status_data else 0
    peer_acc = peer_data['accepted'] if peer_data else 0

    if my_acc == 1 and peer_acc == 1:
        st.session_state.session_step = "live"
        st.rerun()
    elif my_acc == 1:
        st.info("Synchronizing with peer...")
        time.sleep(2)
        st.rerun()
    else:
        if st.button("Establish Link"):
            run_query("UPDATE profiles SET accepted=1 WHERE user_id=?", (st.session_state.user_id,), commit=True)
            st.rerun()
        if st.button("Abort"):
            run_query("UPDATE profiles SET status='active', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,), commit=True)
            st.session_state.session_step = "discovery"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def render_live_chat():
    msgs = run_query("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                    (st.session_state.current_match_id,), fetchall=True)
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for m in msgs:
        cls = "bubble-me" if m['sender'] == st.session_state.user_name else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{m["sender"]}</b><br>{m["message"]}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Node: {st.session_state.peer_info['name']}")
    render_live_chat()
    msg = st.text_input("Data Entry", key="chat_input", label_visibility="collapsed")
    if st.button("Transmit"):
        if msg:
            run_query("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                     (st.session_state.current_match_id, st.session_state.user_name, msg, int(time.time())), commit=True)
            st.rerun()
    st.divider()
    if st.button("Terminate Connection"):
        st.session_state.session_step = "rating"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_rating():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Performance Review")
    rating = st.select_slider("Rate Partner Efficiency", options=[1, 2, 3, 4, 5], value=5)
    feedback = st.text_area("Observations")
    if st.button("Submit Review"):
        run_query("INSERT INTO session_ratings (match_id, rater_id, rating, feedback) VALUES (?,?,?,?)",
                 (st.session_state.current_match_id, st.session_state.user_id, rating, feedback), commit=True)
        msgs = run_query("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,), fetchall=True)
        transcript = " ".join([m['message'] for m in msgs]) if msgs else "No transcript"
        prompt = f"Create a JSON list of 3 MCQs based on: {transcript}. Format: [{{'question':'', 'options':['',''], 'answer':''}}]"
        try:
            res = ask_ai(prompt)
            st.session_state.quiz_data = json.loads(res[res.find('['):res.rfind(']')+1])
        except:
            st.session_state.quiz_data = []
        st.session_state.session_step = "quiz"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    inject_emerald_theme()
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Knowledge Check")
    quiz = st.session_state.get('quiz_data', [])
    if not quiz:
        st.write("Verification data unavailable.")
        if st.button("Continue"): st.session_state.quiz_done = True
    else:
        with st.form("quiz_form"):
            user_ans = []
            for i, q in enumerate(quiz):
                st.write(f"{i+1}. {q['question']}")
                user_ans.append(st.radio("Options", q['options'], key=f"q_{i}"))
            if st.form_submit_button("Submit Verification"):
                score = sum(1 for i, q in enumerate(quiz) if user_ans[i] == q['answer'])
                st.success(f"Final Score: {score}/{len(quiz)}")
                st.session_state.quiz_done = True
    if st.session_state.get('quiz_done'):
        if st.button("Return to Discovery Mode"):
            run_query("UPDATE profiles SET status='active', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,), commit=True)
            st.session_state.session_step = "discovery"
            del st.session_state.quiz_done
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

def matchmaking_page():
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"
    res = run_query("SELECT status, match_id FROM profiles WHERE user_id=?", (st.session_state.user_id,), fetchone=True)
    if res and res.get('status') == 'confirming' and st.session_state.session_step == "discovery":
        peer = run_query("SELECT a.name, p.user_id FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.match_id=? AND p.user_id!=?", (res['match_id'], st.session_state.user_id), fetchone=True)
        if peer:
            st.session_state.peer_info = {"id": peer['user_id'], "name": peer['name']}
            st.session_state.current_match_id = res['match_id']
            st.session_state.session_step = "confirmation"
            st.rerun()
    steps = {"discovery": show_discovery, "confirmation": show_confirmation, "live": show_live_session, "rating": show_rating, "quiz": show_quiz}
    steps.get(st.session_state.session_step, show_discovery)()
