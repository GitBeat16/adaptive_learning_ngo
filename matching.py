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
# DATABASE SCHEMA AUTO-FIX
# =========================================================
def sync_db_schema():
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(profiles)")
    cols = [c[1] for c in cursor.fetchall()]
    updates = {
        "status": "TEXT DEFAULT 'waiting'",
        "match_id": "TEXT",
        "interests": "TEXT DEFAULT 'General Study'",
        "bio": "TEXT DEFAULT 'Ready to learn!'"
    }
    for col, definition in updates.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE profiles ADD COLUMN {col} {definition}")
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
# ADVANCED EMERALD STYLING
# =========================================================
st.markdown("""
    <style>
    /* Main App Background */
    .stApp { background-color: #f0fdf4; }
    
    /* Custom Card Styling */
    .glass-card {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 15px;
        padding: 25px;
        border: 1px solid #d1fae5;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    
    /* Emerald Button Overrides */
    div.stButton > button:first-child {
        background-color: #10b981;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        width: 100%;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    div.stButton > button:hover {
        background-color: #059669;
        border: none;
        transform: scale(1.02);
    }
    
    /* Chat Bubbles */
    .chat-container {
        background: #ffffff;
        border-radius: 15px;
        height: 450px;
        padding: 20px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        border: 1px solid #e5e7eb;
    }
    .bubble {
        padding: 12px 16px;
        border-radius: 18px;
        margin-bottom: 10px;
        max-width: 80%;
        font-size: 14px;
        line-height: 1.4;
    }
    .bubble-me {
        background: #10b981;
        color: white;
        align-self: flex-end;
        border-bottom-right-radius: 2px;
    }
    .bubble-peer {
        background: #f1f5f9;
        color: #1e293b;
        align-self: flex-start;
        border-bottom-left-radius: 2px;
    }
    
    /* Progress Stepper */
    .stepper {
        display: flex;
        justify-content: space-between;
        margin-bottom: 30px;
        font-size: 12px;
        color: #64748b;
    }
    .step-active { color: #10b981; font-weight: bold; border-bottom: 2px solid #10b981; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# UTILITIES
# =========================================================
def ensure_state():
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"
    if "ai_history" not in st.session_state: st.session_state.ai_history = []

def reset_matchmaking():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for key in ["current_match_id", "peer_info", "quiz_data", "summary"]:
        st.session_state[key] = None
    st.session_state.session_step = "discovery"
    st.rerun()

# =========================================================
# UI MODULES
# =========================================================
def render_stepper(current_step):
    steps = ["Discovery", "Confirm", "Live Session", "Summary", "Quiz"]
    cols = st.columns(len(steps))
    for i, s in enumerate(steps):
        is_active = "step-active" if s.lower() in current_step.lower() else ""
        cols[i].markdown(f"<div class='stepper {is_active}'>{i+1}. {s}</div>", unsafe_allow_html=True)

def show_discovery():
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Find Your Study Soulmate")
    st.write("Our AI analyzes interests, goals, and learning styles to find your perfect match.")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        if st.button("Find My Partner"):
            peer = conn.execute("""
                SELECT p.user_id, a.name, p.bio, p.interests 
                FROM profiles p JOIN auth_users a ON a.id=p.user_id 
                WHERE p.status='waiting' AND p.user_id != ? LIMIT 1
            """, (st.session_state.user_id,)).fetchone()
            
            if peer:
                st.session_state.peer_info = {"id": peer[0], "name": peer[1], "bio": peer[2], "ints": peer[3]}
                st.session_state.current_match_id = f"live_{int(time.time())}"
                st.session_state.session_step = "confirmation"
                st.rerun()
            else:
                st.info("No one is online. We've listed you as 'Searching'!")
                conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
                conn.commit()
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    p = st.session_state.peer_info
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"### {p['name'][0].upper()}") # Avatar placeholder
        st.write(f"**{p['name']}**")
    with c2:
        st.success(f"**94% Match Found**")
        st.write(f"**Interests:** {p['ints']}")
        st.caption(f"_{p['bio']}_")
    
    st.divider()
    btn1, btn2 = st.columns(2)
    if btn1.button("Start Session"):
        st.balloons()
        time.sleep(1)
        st.session_state.session_step = "live"
        st.rerun()
    if btn2.button("Skip"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def live_chat_area():
    messages = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                            (st.session_state.current_match_id,)).fetchall()
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    for s, m in messages:
        cl = "bubble-me" if s == st.session_state.user_name else "bubble-peer"
        st.markdown(f'<div class="bubble {cl}"><b>{s}</b><br>{m}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    col_h, col_e = st.columns([3, 1])
    col_h.subheader(f"Session with {st.session_state.peer_info['name']}")
    if col_e.button("Finish Session"):
        st.session_state.session_step = "summary"
        st.rerun()

    live_chat_area()

    # Input Dock
    with st.container():
        st.markdown("<div style='background:#fff; padding:15px; border-radius:15px; border:1px solid #e5e7eb;'>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([4, 1, 1])
        with c1: msg = st.text_input("Message", placeholder="Share an idea...", label_visibility="collapsed", key="chat_msg")
        with c2: st.file_uploader("📂", label_visibility="collapsed")
        with c3:
            if st.button("Send"):
                if msg:
                    conn.execute("INSERT INTO messages (match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                                (st.session_state.current_match_id, st.session_state.user_name, msg, int(time.time())))
                    conn.commit()
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

def show_summary():
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Session Recap")
    if not st.session_state.get("summary"):
        with st.spinner("Synthesizing session details..."):
            history = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
            st.session_state.summary = ask_ai(f"Summarize this study session: {' '.join([m[0] for m in history])}")
    
    st.info(st.session_state.summary)
    st.write("---")
    st.write("How was your partner?")
    st.feedback("stars")
    
    if st.button("Take the Knowledge Quiz"):
        st.session_state.session_step = "quiz"
        st.rerun()
    if st.button("Close"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

def show_quiz():
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    st.subheader("Post-Session Quiz")
    if not st.session_state.get("quiz_data"):
        history = conn.execute("SELECT message FROM messages WHERE match_id=?", (st.session_state.current_match_id,)).fetchall()
        chat_txt = " ".join([m[0] for m in history])
        prompt = f"Create 3 MCQ questions from: {chat_txt}. Return JSON ONLY: [{{'q':'..','options':['..','..'],'correct':'..'}},...]"
        try:
            res = ask_ai(prompt)
            st.session_state.quiz_data = json.loads(res.replace("```json", "").replace("```", ""))
        except:
            st.error("Quiz unavailable for this session.")
            if st.button("Back"): reset_matchmaking()
            return

    score = 0
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.quiz_data):
            ans = st.radio(f"**Q{i+1}:** {q['q']}", q['options'])
            if ans == q['correct']: score += 1
        if st.form_submit_button("Submit Results"):
            if score == 3:
                st.balloons()
                st.success("Perfect! You've mastered this topic.")
            else: st.info(f"Final Score: {score}/3")
    
    if st.button("Exit Quiz"): reset_matchmaking()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# ENTRY POINT
# =========================================================
def matchmaking_page():
    ensure_state()
    
    # Sidebar AI (Always Present)
    with st.sidebar:
        st.title("AI Tutor")
        st.write("---")
        q = st.text_area("Need help during your session?", placeholder="Ask me anything...")
        if st.button("Get AI Assistance"):
            if q:
                ans = ask_ai(q)
                st.session_state.ai_history.append({"q": q, "a": ans})
        
        for item in reversed(st.session_state.ai_history[-2:]):
            with st.expander(f"Q: {item['q'][:20]}...", expanded=False):
                st.write(item['a'])

    # Main Router
    render_stepper(st.session_state.session_step)
    
    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    elif step == "quiz": show_quiz()

if __name__ == "__main__":
    matchmaking_page()
