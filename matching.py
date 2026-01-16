import streamlit as st
import time
import os
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
POLL_INTERVAL = 3

# =========================================================
# SYSTEM & STATE
# =========================================================
def now(): return int(time.time())

def init_state():
    defaults = {
        "current_match_id": None, "session_ended": False, "chat_log": [],
        "last_msg_ts": 0, "last_poll": 0, "summary": None, "quiz": None,
        "rating_given": False, "ai_chat": [], "proposed_match": None
    }
    for k, v in defaults.items(): st.session_state.setdefault(k, v)

def reset_matchmaking():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for k in list(st.session_state.keys()):
        if k not in ["user_id", "user_name", "logged_in", "page"]: del st.session_state[k]
    st.rerun()

# =========================================================
# EMERALD THEME & ANIMATION CSS
# =========================================================
st.markdown("""
    <style>
    /* Global Styles */
    .stApp { background-color: #fcfdfd; }
    h1, h2, h3 { color: #064e3b; font-family: 'Inter', sans-serif; }
    
    /* Emerald Button with Pulse Animation */
    div.stButton > button {
        background-color: #10b981;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s ease;
        font-weight: 500;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #059669;
        box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.2);
        transform: translateY(-1px);
    }
    div.stButton > button:active {
        transform: scale(0.98);
        background-color: #047857;
    }

    /* Minimal Chat Bubbles */
    .chat-container { border: 1px solid #ecfdf5; border-radius: 12px; padding: 20px; background: white; }
    .msg-box { padding: 12px 16px; border-radius: 12px; margin-bottom: 10px; font-size: 0.95rem; line-height: 1.5; }
    .user-msg { background-color: #f1f5f9; color: #1e293b; align-self: flex-end; border-bottom-right-radius: 2px; }
    .partner-msg { background-color: #ecfdf5; color: #065f46; align-self: flex-start; border-bottom-left-radius: 2px; }
    
    /* AI Sidebar Sidebar Minimalist */
    [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# COMPONENTS
# =========================================================
def ai_sidebar():
    with st.sidebar:
        st.markdown("### AI assistant")
        q = st.text_input("Ask a concept...", key="ai_q", label_visibility="collapsed")
        if st.button("Query AI") and q:
            ans = ask_ai(q)
            st.session_state.ai_chat.insert(0, (q, ans))
        
        for q_h, a_h in st.session_state.ai_chat[:2]:
            with st.container(border=True):
                st.markdown(f"**Q:** {q_h}")
                st.markdown(f"**A:** {a_h}")

def poll_sync(match_id):
    if now() - st.session_state.last_poll > POLL_INTERVAL:
        rows = conn.execute("SELECT sender, message, created_ts FROM messages WHERE match_id=? AND created_ts > ? ORDER BY created_ts", (match_id, st.session_state.last_msg_ts)).fetchall()
        if rows:
            for s, m, ts in rows:
                st.session_state.chat_log.append((s, m))
                st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)
            st.session_state.last_poll = now()
            st.rerun()
        st.session_state.last_poll = now()

# =========================================================
# MAIN INTERFACE
# =========================================================
def matchmaking_page():
    if not st.session_state.get("user_id"): st.stop()
    init_state()
    ai_sidebar()

    # --- PHASE 1: DISCOVERY & SYNC ---
    if not st.session_state.current_match_id:
        st.markdown("# Study discovery")
        st.markdown("Connect with a peer to begin a synchronized learning session.")
        
        # Auto-check if someone else invited us
        incoming = conn.execute("SELECT match_id FROM profiles WHERE user_id=? AND status='matched'", (st.session_state.user_id,)).fetchone()
        if incoming:
            st.session_state.current_match_id = incoming[0]
            st.rerun()

        if not st.session_state.proposed_match:
            if st.button("Find compatible partner"):
                res = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.status='waiting' AND p.user_id!=?", (st.session_state.user_id,)).fetchone()
                if res:
                    st.session_state.proposed_match = {"id": res[0], "name": res[1]}
                    st.rerun()
                else: st.toast("Searching for active peers...")
        else:
            with st.container(border=True):
                st.markdown(f"### Found: {st.session_state.proposed_match['name']}")
                st.write("Both users must accept to initialize the live session.")
                c1, c2 = st.columns(2)
                if c1.button("Accept session"):
                    mid = f"sync_{min(st.session_state.user_id, st.session_state.proposed_match['id'])}_{now()}"
                    conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id IN (?,?)", (mid, st.session_state.user_id, st.session_state.proposed_match['id']))
                    conn.commit()
                    st.session_state.current_match_id = mid
                    st.balloons()
                    st.rerun()
                if c2.button("Decline", type="secondary"): 
                    st.session_state.proposed_match = None
                    st.rerun()

    # --- PHASE 2: LIVE SYNC SESSION ---
    elif st.session_state.current_match_id and not st.session_state.session_ended:
        poll_sync(st.session_state.current_match_id)
        
        col_main, col_side = st.columns([2, 1], gap="large")
        
        with col_main:
            st.markdown("### Collaborative chat")
            for sender, msg in st.session_state.chat_log:
                css_class = "user-msg" if sender == st.session_state.user_name else "partner-msg"
                st.markdown(f"<div class='msg-box {css_class}'><b>{sender}</b><br>{msg}</div>", unsafe_allow_html=True)
            
            with st.form("chat_input", clear_on_submit=True):
                msg = st.text_input("Your message", placeholder="Type something...", label_visibility="collapsed")
                if st.form_submit_button("Send"):
                    conn.execute("INSERT INTO messages(match_id, sender, message, created_ts) VALUES (?,?,?,?)", (st.session_state.current_match_id, st.session_state.user_name, msg, now()))
                    conn.commit()
                    st.rerun()

        with col_side:
            st.markdown("### Resources")
            with st.container(border=True):
                file = st.file_uploader("Upload material", label_visibility="collapsed")
                if file:
                    with open(os.path.join(UPLOAD_DIR, file.name), "wb") as f: f.write(file.getbuffer())
                    st.toast("File synchronized")
            
            st.divider()
            if st.button("Complete session", type="primary"):
                chat_text = " ".join([m for _, m in st.session_state.chat_log])
                st.session_state.summary = ask_ai("Summarize: " + chat_text)
                st.session_state.quiz = ask_ai("MCQ Quiz: " + chat_text)
                st.session_state.session_ended = True
                st.rerun()

    # --- PHASE 3: RECAP ---
    else:
        st.markdown("# Session recap")
        st.markdown(st.session_state.summary)
        
        if not st.session_state.rating_given:
            st.markdown("#### Rate your partner")
            rating = st.feedback("stars")
            if rating is not None:
                st.session_state.rating_given = True
                st.success("Rating submitted")

        st.divider()
        st.markdown("#### Assessment")
        st.write(st.session_state.quiz)
        
        score = st.number_input("Final score (out of 3)", 0, 3)
        if st.button("Check results"):
            if score == 3: 
                st.balloons()
                st.success("Perfect mastery!")
        
        if st.button("Return to dashboard"): reset_matchmaking()

matchmaking_page()
