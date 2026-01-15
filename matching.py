import streamlit as st
import time
from database import cursor, conn
from ai_helper import ask_ai

SESSION_TIMEOUT_SEC = 60 * 60   # 1 hour
POLL_INTERVAL_SEC = 3           # real-time polling

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def init_state():
    defaults = {
        "user_id": None,
        "user_name": "",
        "current_match_id": None,
        "session_start_time": None,
        "session_ended": False,
        "just_matched": False,
        "partner_joined": False,
        "chat_log": [],
        "last_msg_ts": 0,          # ✅ REQUIRED FOR LIVE CHAT
        "proposed_match": None,
        "proposed_score": None,
        "show_quiz": False,
        "quiz_raw": "",
        "quiz_answers": {},
        "ai_chat": [],
        "last_poll": 0
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def update_last_seen():
    if st.session_state.user_id:
        cursor.execute(
            "UPDATE profiles SET last_seen=? WHERE user_id=?",
            (now(), st.session_state.user_id)
        )
        conn.commit()

def normalize_match(m):
    if not m:
        return None
    if isinstance(m, dict):
        return m
    if isinstance(m, (tuple, list)) and len(m) >= 5:
        return {
            "user_id": m[0],
            "name": m[1],
            "role": m[2],
            "grade": m[3],
            "time": m[4],
            "strong": (m[7] if len(m) > 7 else "").split(","),
            "weak": (m[6] if len(m) > 6 else "").split(","),
        }
    return None

# =========================================================
# REAL-TIME CHECKS (NO AUTOREFRESH)
# =========================================================
def should_poll():
    return now() - st.session_state.last_poll >= POLL_INTERVAL_SEC

def poll_tick():
    st.session_state.last_poll = now()
    st.rerun()

def check_if_matched():
    cursor.execute("""
        SELECT match_id FROM profiles
        WHERE user_id=? AND status='matched'
    """, (st.session_state.user_id,))
    row = cursor.fetchone()
    if row and not st.session_state.current_match_id:
        st.session_state.current_match_id = row[0]
        st.session_state.just_matched = True
        st.session_state.session_start_time = now()
        st.rerun()

def check_partner_joined(match_id):
    cursor.execute("""
        SELECT last_seen FROM profiles
        WHERE match_id=? AND user_id!=?
    """, (match_id, st.session_state.user_id))
    row = cursor.fetchone()
    return bool(row and (now() - (row[0] or 0)) <= 10)

# =========================================================
# LIVE CHAT (DB BACKED)
# =========================================================
def fetch_new_messages(match_id):
    cursor.execute("""
        SELECT sender, message, created_ts
        FROM messages
        WHERE match_id=?
          AND created_ts > ?
        ORDER BY created_ts ASC
    """, (match_id, st.session_state.last_msg_ts))
    rows = cursor.fetchall()

    for sender, msg, ts in rows:
        st.session_state.chat_log.append((sender, msg))
        st.session_state.last_msg_ts = max(st.session_state.last_msg_ts, ts)

# =========================================================
# MATCHING LOGIC
# =========================================================
def load_waiting_profiles():
    cursor.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects, p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id=p.user_id
        WHERE p.status='waiting'
          AND p.match_id IS NULL
    """)
    rows = cursor.fetchall()

    users = []
    for r in rows:
        users.append({
            "user_id": r[0],
            "name": r[1],
            "role": r[2],
            "grade": r[3],
            "time": r[4],
            "strong": (r[7] or r[5] or "").split(","),
            "weak": (r[6] or "").split(",")
        })
    return users

def score(u1, u2):
    s = 0
    s += len(set(u1["weak"]) & set(u2["strong"])) * 25
    s += len(set(u2["weak"]) & set(u1["strong"])) * 25
    if u1["grade"] == u2["grade"]:
        s += 10
    if u1["time"] == u2["time"]:
        s += 10
    return s

def find_best_match(current):
    best, best_score = None, -1
    for u in load_waiting_profiles():
        if u["user_id"] == current["user_id"]:
            continue
        sc = score(current, u)
        if sc > best_score:
            best, best_score = u, sc
    return best, best_score

# =========================================================
# AI FEATURES
# =========================================================
def generate_summary(chat):
    return ask_ai(
        "Summarize this study session in 5 bullet points:\n" +
        "\n".join([m for _, m in chat][-20:])
    )

def generate_quiz(chat):
    return ask_ai("""
Create exactly 4 MCQ questions from this discussion.
FORMAT STRICTLY AS:
Q1: question
A) option
B) option
C) option
D) option
Answer: A
""" + "\n" + "\n".join([m for _, m in chat][-30:]))

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    init_state()
    update_last_seen()

    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE user_id=? AND status!='matched'
    """, (st.session_state.user_id,))
    conn.commit()

    if should_poll():
        check_if_matched()
        poll_tick()

    st.title("🤝 Study Matchmaking")

    # =====================================================
    # ACTIVE SESSION
    # =====================================================
    if st.session_state.current_match_id and not st.session_state.session_ended:
        elapsed = now() - st.session_state.session_start_time
        remaining = max(0, SESSION_TIMEOUT_SEC - elapsed)
        st.success(f"⏱️ Time left: {remaining//60}m {remaining%60}s")

        fetch_new_messages(st.session_state.current_match_id)

        st.subheader("💬 Study Chat")
        for sender, msg in st.session_state.chat_log[-50:]:
            st.markdown(f"**{sender}:** {msg}")

        msg = st.text_input("Message")
        if st.button("Send") and msg:
            cursor.execute(
                "INSERT INTO messages(match_id, sender, message) VALUES (?,?,?)",
                (st.session_state.current_match_id, st.session_state.user_name, msg)
            )
            conn.commit()
            st.rerun()

        return
