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
# DEFENSIVE DATA FETCHING
# =========================================================
def get_user_status(uid):
    res = conn.execute("SELECT status, accepted, match_id FROM profiles WHERE user_id=?", (uid,)).fetchone()
    if res: return res
    conn.execute("INSERT INTO profiles (user_id, status, accepted) VALUES (?, 'active', 0)", (uid,))
    conn.commit()
    return ('active', 0, None)

# =========================================================
# PERMANENT EMERALD UI
# =========================================================
def inject_ui():
    st.markdown("""
        <style>
        .emerald-card {
            background: white !important;
            padding: 30px !important;
            border-radius: 20px !important;
            border-top: 10px solid #10b981 !important;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important;
            margin-bottom: 25px;
        }
        .emerald-card h1, .emerald-card h2, .emerald-card h3 { color: #064e3b !important; font-weight: 800 !important; margin-top: 0px !important; }
        div.stButton > button {
            background-color: #10b981 !important;
            color: white !important;
            border: none !important;
            padding: 12px !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            width: 100% !important;
        }
        .stButton button[kind="secondary"] { background-color: #ef4444 !important; }
        .chat-scroll { background: #f8fafc !important; border: 1px solid #e2e8f0 !important; border-radius: 12px; padding: 15px; height: 350px; overflow-y: auto; margin-bottom: 20px; }
        .bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 10px; max-width: 80%; }
        .bubble-me { background: #10b981; color: white; margin-left: auto; border-bottom-right-radius: 2px; }
        .bubble-peer { background: white; color: #1e293b; border: 1px solid #e2e8f0; border-bottom-left-radius: 2px; }
        .summary-box { background: #f0fdf4; border-left: 5px solid #10b981; padding: 15px; border-radius: 8px; margin: 10px 0; }
        </style>
    """, unsafe_allow_html=True)

# =========================================================
# AI LOGIC
# =========================================================
def generate_session_insight():
    """Fetch chat history and generate AI summary + quiz"""
    msgs = conn.execute("SELECT sender, message FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                       (st.session_state.current_match_id,)).fetchall()
    
    if not msgs:
        return "No conversation recorded.", "N/A"

    chat_transcript = "\n".join([f"{m[0]}: {m[1]}" for m in msgs])
    
    prompt = f"""
    Based on this study session transcript:
    {chat_transcript}
    
    1. Provide a 3-sentence summary of what was learned.
    2. Provide 3 multiple-choice quiz questions based on the topics discussed.
    Format the output clearly with headers.
    """
    return ask_ai(prompt)

# =========================================================
# UI MODULES
# =========================================================

def show_discovery():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Partner Discovery")
    st.write("Scan the network for a compatible peer.")
    conn.execute("UPDATE profiles SET status='waiting' WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()

    if st.button("Search Compatible Partner"):
        peer = conn.execute("""
            SELECT p.user_id, a.name FROM profiles p 
            JOIN auth_users a ON a.id = p.user_id 
            WHERE p.status = 'waiting' AND p.user_id != ? LIMIT 1
        """, (st.session_state.user_id,)).fetchone()
        
        if peer:
            m_id = f"sess_{int(time.time())}"
            st.session_state.peer_info = {"id": peer[0], "name": peer[1]}
            st.session_state.current_match_id = m_id
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, st.session_state.user_id))
            conn.execute("UPDATE profiles SET status='confirming', match_id=?, accepted=0 WHERE user_id=?", (m_id, peer[0]))
            conn.commit()
            st.session_state.session_step = "confirmation"
            st.rerun()
        else:
            st.info("System: Scanning active nodes... No peers found yet.")
    st.markdown("</div>", unsafe_allow_html=True)

def show_confirmation():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Incoming Request")
    st.write(f"Do you want to start a session with **{st.session_state.peer_info['name']}**?")
    
    _, my_acc, _ = get_user_status(st.session_state.user_id)
    _, peer_acc, _ = get_user_status(st.session_state.peer_info['id'])

    if my_acc == 1 and peer_acc == 1:
        st.session_state.session_step = "live"
        st.rerun()
    elif my_acc == 1:
        st.warning(f"Waiting for {st.session_state.peer_info['name']} to accept...")
        time.sleep(2)
        st.rerun()
    else:
        if st.button("Accept & Connect"):
            conn.execute("UPDATE profiles SET accepted=1 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.rerun()
        if st.button("Decline"):
            conn.execute("UPDATE profiles SET status='waiting', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
            conn.commit()
            st.session_state.session_step = "discovery"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

@st.fragment(run_every=2)
def render_live_chat():
    msgs = conn.execute("SELECT sender, message, file_path FROM messages WHERE match_id=? ORDER BY created_ts ASC", 
                       (st.session_state.current_match_id,)).fetchall()
    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for sender, msg, f_path in msgs:
        is_me = (sender == st.session_state.user_name)
        cls = "bubble-me" if is_me else "bubble-peer"
        st.markdown(f'<div class="bubble {cls}"><b>{sender}</b><br>{msg if msg else ""}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

def show_live_session():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title(f"Collaborating: {st.session_state.peer_info['name']}")
    render_live_chat()
    
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        msg = st.text_input("Message", label_visibility="collapsed", placeholder="Type...", key="chat_input")
    with c2:
        up = st.file_uploader("File", label_visibility="collapsed", key="file_up")
    with c3:
        if st.button("Send"):
            path = None
            if up:
                path = os.path.join(UPLOAD_DIR, up.name)
                with open(path, "wb") as f: f.write(up.getbuffer())
            if msg or up:
                conn.execute("INSERT INTO messages (match_id, sender, message, file_path, created_ts) VALUES (?,?,?,?,?)",
                            (st.session_state.current_match_id, st.session_state.user_name, msg, path, int(time.time())))
                conn.commit()
                st.rerun()

    st.divider()
    # END SESSION BUTTON
    if st.button("🏁 End Session", type="secondary"):
        with st.spinner("Generating AI Session Insights..."):
            st.session_state.session_insight = generate_session_insight()
        
        # Reset DB status for both users
        conn.execute("UPDATE profiles SET status='active', match_id=NULL, accepted=0 WHERE user_id=?", (st.session_state.user_id,))
        conn.commit()
        st.session_state.session_step = "summary"
        st.rerun()
        
    st.markdown("</div>", unsafe_allow_html=True)

def show_summary():
    st.markdown("<div class='emerald-card'>", unsafe_allow_html=True)
    st.title("Session Complete! 🎉")
    st.write("Here is your AI-generated summary and quiz based on the conversation.")
    
    st.markdown(f"<div class='summary-box'>{st.session_state.get('session_insight', 'No data available.')}</div>", unsafe_allow_html=True)
    
    if st.button("Back to Matchmaking"):
        st.session_state.session_step = "discovery"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MAIN ROUTER
# =========================================================
def matchmaking_page():
    inject_ui()
    if "session_step" not in st.session_state: st.session_state.session_step = "discovery"

    step = st.session_state.session_step
    if step == "discovery": show_discovery()
    elif step == "confirmation": show_confirmation()
    elif step == "live": show_live_session()
    elif step == "summary": show_summary()
    else: 
        st.session_state.session_step = "discovery"
        st.rerun()
