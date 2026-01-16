import streamlit as st
import time
import os
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

POLL_INTERVAL = 3

# =========================================================
# DATABASE & LOGIC HELPERS
# =========================================================
def now():
    return int(time.time())

def init_state():
    defaults = {
        "current_match_id": None,
        "session_ended": False,
        "chat_log": [],
        "last_msg_ts": 0,
        "last_poll": 0,
        "summary": None,
        "quiz": None,
        "rating_given": False,
        "ai_chat": [],
        "proposed_match": None,
        "has_accepted": False
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def reset_matchmaking():
    conn.execute("UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?", (st.session_state.user_id,))
    conn.commit()
    for k in list(st.session_state.keys()):
        if k not in ["user_id", "user_name", "logged_in", "page"]:
            del st.session_state[k]
    st.rerun()

# =========================================================
# UI STYLING
# =========================================================
st.markdown("""
    <style>
    .stChatFloatingInputContainer { background-color: rgba(0,0,0,0); }
    .status-box { padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; background-color: #ffffff; }
    .chat-msg { margin: 10px 0; padding: 10px; border-radius: 5px; }
    .user-msg { background-color: #f0f2f6; border-left: 5px solid #007bff; }
    .partner-msg { background-color: #ffffff; border-left: 5px solid #28a745; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# COMPONENTS
# =========================================================
def ai_panel():
    with st.sidebar:
        st.subheader("AI Study Assistant")
        q = st.text_input("Ask AI a question", key="side_ai", placeholder="Type here...")
        if st.button("Query") and q:
            res = ask_ai(q)
            st.session_state.ai_chat.insert(0, (q, res))
        
        for q_h, a_h in st.session_state.ai_chat[:2]:
            st.markdown(f"**Q:** {q_h}")
            st.markdown(f"**A:** {a_h}")
            st.divider()

def handle_polling(match_id):
    if now() - st.session_state.last_poll > POLL_INTERVAL:
        # Check for new messages
        rows = conn.execute("""
            SELECT sender, message, created_ts FROM messages 
            WHERE match_id=? AND created_ts > ? ORDER BY created_ts
        """, (match_id, st.session_state.last_msg_ts)).fetchall()
        
        if rows:
            for s, m, ts in rows:
                st.session_state.chat_log.append((s, m))
                st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)
            st.session_state.last_poll = now()
            st.rerun()
        st.session_state.last_poll = now()

# =========================================================
# MAIN PAGE FLOW
# =========================================================
def matchmaking_page():
    if not st.session_state.get("user_id"):
        st.stop()
    
    init_state()
    ai_panel()

    # --- PHASE 1: SEARCHING & HANDSHAKE ---
    if not st.session_state.current_match_id:
        st.title("Partner Discovery")
        
        # Check if someone else matched with us while we were waiting
        check_match = conn.execute("SELECT match_id FROM profiles WHERE user_id=? AND status='matched'", 
                                   (st.session_state.user_id,)).fetchone()
        
        if check_match:
            st.session_state.current_match_id = check_match[0]
            st.rerun()

        if not st.session_state.proposed_match:
            if st.button("Search for Compatible Partner", type="primary"):
                # Logic to find a user (Simplified for example, use your existing SQL logic)
                res = conn.execute("SELECT p.user_id, a.name FROM profiles p JOIN auth_users a ON a.id=p.user_id WHERE p.status='waiting' AND p.user_id!=?", (st.session_state.user_id,)).fetchone()
                if res:
                    st.session_state.proposed_match = {"id": res[0], "name": res[1]}
                    st.rerun()
                else:
                    st.info("Searching for active students...")
                    time.sleep(2)
                    st.rerun()
        else:
            # HANDSHAKE UI
            target = st.session_state.proposed_match
            st.markdown(f"### Connection Request: {target['name']}")
            st.write("Both users must accept to begin the synchronized session.")
            
            col1, col2 = st.columns(2)
            if col1.button("Accept Connection", use_container_width=True):
                mid = f"session_{min(st.session_state.user_id, target['id'])}_{max(st.session_state.user_id, target['id'])}"
                conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id=?", (mid, st.session_state.user_id))
                conn.execute("UPDATE profiles SET status='matched', match_id=? WHERE user_id=?", (mid, target['id']))
                conn.commit()
                st.session_state.current_match_id = mid
                st.balloons()
                st.rerun()
            
            if col2.button("Decline", use_container_width=True):
                st.session_state.proposed_match = None
                st.rerun()

    # --- PHASE 2: LIVE SESSION ---
    elif st.session_state.current_match_id and not st.session_state.session_ended:
        handle_polling(st.session_state.current_match_id)
        
        st.title("Live Collaboration")
        st.caption(f"Match ID: {st.session_state.current_match_id}")

        col_chat, col_tools = st.columns([2, 1])

        with col_chat:
            st.subheader("Discussion")
            for sender, msg in st.session_state.chat_log:
                div_class = "user-msg" if sender == st.session_state.user_name else "partner-msg"
                st.markdown(f"<div class='chat-msg {div_class}'><b>{sender}</b><br>{msg}</div>", unsafe_allow_html=True)

            with st.form("send_msg", clear_on_submit=True):
                m_text = st.text_input("Type your message...", label_visibility="collapsed")
                if st.form_submit_button("Send Message"):
                    conn.execute("INSERT INTO messages(match_id, sender, message, created_ts) VALUES (?,?,?,?)",
                                 (st.session_state.current_match_id, st.session_state.user_name, m_text, now()))
                    conn.commit()
                    st.rerun()

        with col_tools:
            st.subheader("Session Tools")
            with st.container(border=True):
                st.write("File Exchange")
                up = st.file_uploader("Upload PDF/Image", label_visibility="collapsed")
                if up:
                    fpath = os.path.join(UPLOAD_DIR, f"{st.session_state.current_match_id}_{up.name}")
                    with open(fpath, "wb") as f:
                        f.write(up.getbuffer())
                    st.success("File shared.")
            
            st.divider()
            if st.button("End Session", type="primary"):
                # Wrap up logic
                full_text = " ".join([m for _, m in st.session_state.chat_log])
                st.session_state.summary = ask_ai("Summarize this: " + full_text)
                st.session_state.quiz = ask_ai("Create 3 MCQs based on: " + full_text)
                st.session_state.session_ended = True
                st.rerun()

    # --- PHASE 3: POST-SESSION ---
    else:
        st.title("Session Complete")
        
        st.markdown("### Summary")
        st.info(st.session_state.summary)

        if not st.session_state.rating_given:
            st.subheader("Rate your Partner")
            stars = st.feedback("stars")
            if stars is not None:
                conn.execute("INSERT INTO session_ratings(match_id, rater_id, rating) VALUES (?,?,?)",
                             (st.session_state.current_match_id, st.session_state.user_id, stars + 1))
                conn.commit()
                st.session_state.rating_given = True
                st.success("Rating saved.")

        st.divider()
        st.subheader("Knowledge Check")
        st.write(st.session_state.quiz)
        
        score = st.number_input("How many did you get right? (0-3)", 0, 3)
        if st.button("Submit Score"):
            if score == 3:
                st.balloons()
                st.success("Perfect score!")
            else:
                st.write("Good effort! Review the summary again.")

        if st.button("Finish & Exit"):
            reset_matchmaking()

matchmaking_page()
