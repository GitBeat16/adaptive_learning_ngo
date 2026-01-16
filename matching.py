import streamlit as st
import time
import os
import json
from database import conn
from ai_helper import ask_ai

# Ensure upload directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================================================
# DATABASE SCHEMA AUTO-FIX (Prevents OperationalError)
# =========================================================
def sync_db_schema():
    cursor = conn.cursor()
    # Check Profiles table
    cursor.execute("PRAGMA table_info(profiles)")
    cols = [c[1] for c in cursor.fetchall()]
    
    # Add missing columns if they don't exist
    updates = {
        "status": "TEXT DEFAULT 'waiting'",
        "match_id": "TEXT",
        "interests": "TEXT DEFAULT 'General Study'",
        "bio": "TEXT DEFAULT 'No bio provided'"
    }
    for col, definition in updates.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} {definition}")
    
    # Ensure messages table exists for live chat
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT,
            sender TEXT,
            message TEXT,
            created_ts INTEGER
        )
    """)
    conn.commit()

sync_db_schema()

# =========================================================
# CSS STYLING
# =========================================================
st.markdown("""
    <style>
    .stButton > button { border-radius: 8px; font-weight: 600; }
    .chat-stage {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        height: 380px;
        overflow-y: auto;
        padding: 20px;
        margin-bottom: 10px;
        display: flex;
        flex-direction: column;
    }
    .msg-box { padding: 10px 15px; border-radius: 15px; margin-bottom: 8px; max-width: 80%; }
    .my-msg { background-color: #10b981; color: white; align-self: flex-end; border-bottom-right-radius: 2px; }
    .peer-msg { background-color: #ffffff; color: #1f2937; align-self: flex-start; border-bottom-left-radius: 2px; border: 1px solid #e2e8f0; }
    .comp-card { background: white; padding: 15px; border-radius: 10px; border-left: 5px solid #10b981; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# HELPERS & STATE
# =========================================================
def ensure_state():
    defaults = {
        "session_step": "discovery", "current_match_id": None, 
        "peer_info": None, "ai_history": [], "quiz_data": None, "summary": ""
    }
    for key, val in defaults.items():
        if key not in st.session_state: st.session_state[key] = val

def reset_all():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for key in ["session_step", "current_match_id", "peer_info", "quiz_data", "summary"]:
        st.session_state[key] = None if key != "session_step" else "discovery"
    st.rerun()

# =========================================================
# SIDEBAR AI ASSISTANT
# =========================================================
def render_sidebar():
    with st.sidebar:
        st.header("🤖 AI Study Assistant")
        q = st.text_area("Ask anything...", height=70, key="ai_input_side")
        if st.button("Ask AI", use_container_width=True):
            if q:
                with st.spinner("AI is thinking..."):
                    ans = ask_ai(q)
                    st.session_state.ai_history.append({"q": q, "a": ans})
        
        for item in reversed(st.session_state.ai_history[-2:]):
            with st.expander(f"Last: {item['q'][:20]}...", expanded=False):
                st.write(item['a'])

# =========================================================
# PAGE COMPONENTS
# =========================================================

def show_discovery():
    st.title("Peer Matchmaking")
    st.write("Connect with a partner based on your study compatibility.")
    
    if st.button("Search for Compatible Partner", type="primary"):
        # We join with auth_users to get the real name
        peer = conn.execute("""
            SELECT p.user_id, a.name, p.bio, p.interests 
            FROM profiles p JOIN auth_users a ON a.id=p.user_id 
            WHERE p.status='waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()

        if peer:
            st.session_state.peer_info = {"id": peer[0], "name": peer[1], "bio": peer[2], "ints": peer[3]}
            st.session_state.current_match_id = f"live_{min(st.session_state.user_id, peer[0])}_{max(st.session_state.user_id, peer[0])}"
            st.session_state.session_step = "confirmation"
            st.rerun()
        else:
            st.warning("Searching... No peers found yet. Your status is now 'Waiting'.")
            conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()

def show_confirmation():
    st.subheader("Compatible Match Found!")
    p = st.session_state.peer_info
    
    st.markdown(f"""
    <div class="comp-card">
        <h3>{p['name']}</h3>
        <p><b>Interests:</b> {p['ints']}</p>
        <p><b>About:</b> {p['bio']}</p>
        <p style="color:#10b981; font-weight:bold;">89% Compatibility Match</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    c1, c2 = st.columns(2)
    if c1.button("✅ Confirm Match", type="primary", use_container_width=True):
        st.balloons()
        time.sleep(1)
        st.session_state.session_step = "live"
        st.rerun()
    if c2.button("❌ Skip", use_container_width=True):
        reset_all()

@st.fragment(run_every=2)
def live_chat_loop():
    messages = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                            (st.session_state.current_match_id,)).fetchall()
    st.markdown('<div class="chat-stage">', unsafe_allow_html=True)
    for s, m in messages:
        cl = "my-msg" if s == st.session_state.user_name else "peer-msg"
        st.markdown(f'<div class="msg-box {cl}"><b>{s}</b><br>{m}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.header("Live Study Room")
    if st.button("End Session"):
        st.session_state.session_step = "summary"
        st.rerun()

    live_chat_loop()

    with st.container():
        col_t, col_f, col_b = st.columns([3, 1, 1])
        with col_t: msg = st.text_input("Message", label_visibility="collapsed", key="live_msg")
        with col_f: st.file_uploader("File", label_visibility="collapsed")
        with col_b:
            if st.button("Send", type="primary", use_container_width=True):
                if msg:
                    conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, msg, int(time.time())))
                    conn.commit()
                    st.rerun()

def show_summary():
    st.title("Session Complete")
    if not st.session_state.summary:
        with st.spinner("Analyzing session..."):
            history = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
            chat_txt = " ".join([m[0] for m in history])
            st.session_state.summary = ask_ai(f"Summarize this study session chat briefly: {chat_txt}")
    
    st.info(st.session_state.summary)
    st.subheader("Rate your experience")
    st.feedback("stars")
    
    if st.button("Generate AI Quiz", type="primary"):
        st.session_state.session_step = "quiz"
        st.rerun()
    if st.button("Back to Matchmaking"):
        reset_all()

def show_quiz():
    st.header("AI Knowledge Check")
    if not st.session_state.quiz_data:
        history = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
        chat_txt = " ".join([m[0] for m in history])
        prompt = f"Create 3 MCQ questions from this study chat: {chat_txt}. Return JSON ONLY: [{{'q':'..','options':['..','..'],'correct':'..'}},...]"
        try:
            res = ask_ai(prompt)
            st.session_state.quiz_data = json.loads(res.replace("```json", "").replace("```", ""))
        except:
            st.error("Could not generate quiz. Chat might be too short.")
            if st.button("Exit"): reset_all()
            return

    score = 0
    with st.form("quiz_ui"):
        for i, q in enumerate(st.session_state.quiz_data):
            ans = st.radio(f"Q{i+1}: {q['q']}", q['options'])
            if ans == q['correct']: score += 1
        if st.form_submit_button("Submit"):
            if score == 3:
                st.balloons()
                st.success("Perfect! You mastered this session.")
            else: st.info(f"You got {score}/3 correct.")

    if st.button("Finish"): reset_all()

# =========================================================
# MAIN ENTRY POINT
# =========================================================
def matchmaking_page():
    ensure_state()
    render_sidebar()
    
    step = st.session_state.session_step
    
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
