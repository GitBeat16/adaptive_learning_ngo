import streamlit as st
import time
import os
import random
from database import conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

POLL_INTERVAL = 3

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def require_login():
    if not st.session_state.get("user_id"):
        st.stop()

def init_state():
    defaults = {
        "current_match_id": None,
        "confirmed": False,
        "session_ended": False,
        "chat_log": [],
        "last_msg_ts": 0,
        "last_poll": 0,
        "summary": None,
        "quiz": None,
        "rating_given": False,
        "ai_chat": [],
        "refresh_key": 0,
        "proposed_match": None,
        "proposed_score": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def should_poll():
    return now() - st.session_state.last_poll >= POLL_INTERVAL

def poll():
    st.session_state.last_poll = now()
    st.rerun()

def reset_matchmaking():
    conn.execute(
        "UPDATE profiles SET status='waiting', match_id=NULL WHERE user_id=?",
        (st.session_state.user_id,)
    )
    conn.commit()

    for k in list(st.session_state.keys()):
        if k not in ["user_id", "user_name", "logged_in", "page"]:
            del st.session_state[k]

    st.rerun()

# =========================================================
# AI CHATBOT
# =========================================================
def ai_chat_ui():
    st.subheader("AI Assistant")
    q = st.text_input("Ask the assistant", key="ai_q")
    if st.button("Send to AI") and q:
        st.session_state.ai_chat.append((q, ask_ai(q)))

    for q, a in st.session_state.ai_chat[-5:]:
        st.markdown(f"**You:** {q}")
        st.markdown(f"**AI:** {a}")

# =========================================================
# MATCHING
# =========================================================
def load_waiting_profiles():
    rows = conn.execute("""
        SELECT a.id, a.name, p.grade, p.time,
               p.strong_subjects, p.weak_subjects
        FROM profiles p
        JOIN auth_users a ON a.id=p.user_id
        WHERE p.user_id!=?
          AND p.status='waiting'
          AND p.match_id IS NULL
    """, (st.session_state.user_id,)).fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r[0],
            "name": r[1],
            "grade": r[2],
            "time": r[3],
            "strong": (r[4] or "").split(","),
            "weak": (r[5] or "").split(","),
        })
    return users

def compatibility(a, b):
    s = 0
    s += len(set(a["weak"]) & set(b["strong"])) * 25
    s += len(set(b["weak"]) & set(a["strong"])) * 25
    if a["grade"] == b["grade"]:
        s += 10
    if a["time"] == b["time"]:
        s += 10
    s += random.randint(0, 5)
    return s

def find_best_match(current):
    best, best_score = None, -1
    for u in load_waiting_profiles():
        sc = compatibility(current, u)
        if sc > best_score:
            best, best_score = u, sc
    return best, best_score

# =========================================================
# CHAT
# =========================================================
def fetch_messages(match_id):
    rows = conn.execute("""
        SELECT sender, message, COALESCE(created_ts,0)
        FROM messages
        WHERE match_id=? AND COALESCE(created_ts,0) > ?
        ORDER BY created_ts
    """, (match_id, st.session_state.last_msg_ts)).fetchall()

    for s, m, ts in rows:
        st.session_state.chat_log.append((s, m))
        st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)

# =========================================================
# STAR RATING
# =========================================================
def star_rating():
    st.write("Rate your mentor")
    cols = st.columns(5)
    for i in range(5):
        if cols[i].button("★", key=f"star_{i}"):
            return i + 1
    return None

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    require_login()
    init_state()

    # ================= EMERALD BUTTON STYLE (SESSION ONLY) =================
    st.markdown("""
    <style>
    .stApp > div:not(section[data-testid="stSidebar"]) .stButton > button {
        background: linear-gradient(135deg,#0f766e,#14b8a6,#22c55e);
        color:white;
        border:none;
        border-radius:999px;
        padding:0.55rem 1.1rem;
        font-weight:600;
        box-shadow:0 6px 18px rgba(20,184,166,.35);
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## Study Matchmaking")
    ai_chat_ui()
    st.divider()

    # ================= FIND PARTNER (VISIBLE ENTRY POINT) =================
    if not st.session_state.confirmed and not st.session_state.proposed_match:
        st.markdown(
            """
            <div style="
                background:#ffffff;
                border-radius:16px;
                padding:1.2rem;
                box-shadow:0 10px 24px rgba(0,0,0,.06);
            ">
            <h4>Find a study partner</h4>
            <p>
            We’ll match you with someone based on subjects, grade, and time slot.
            </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        r = conn.execute("""
            SELECT grade, time, strong_subjects, weak_subjects
            FROM profiles WHERE user_id=?
        """, (st.session_state.user_id,)).fetchone()

        current = {
            "grade": r[0],
            "time": r[1],
            "strong": (r[2] or "").split(","),
            "weak": (r[3] or "").split(","),
        }

        if st.button("Find compatible partner"):
            best, score = find_best_match(current)
            if best:
                st.session_state.proposed_match = best
                st.session_state.proposed_score = score
                st.rerun()
            else:
                st.info("No compatible users right now. Try again shortly.")
        return

    # 👉 EVERYTHING BELOW (confirmation, balloons, live chat, files,
    # 👉 summary, quiz, rating, back to matchmaking) REMAINS UNCHANGED
