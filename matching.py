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

    # ================= UI STYLE (ONLY CHANGE) =================
    st.markdown("""
    <style>
    .stButton > button {
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg,#6366f1,#4f46e5);
        color: white;
        border: none;
        border-radius: 999px;
        padding: 0.55rem 1.1rem;
        font-weight: 600;
        font-size: 0.85rem;
        cursor: pointer;
        transition: transform .2s ease, box-shadow .2s ease;
        box-shadow: 0 6px 18px rgba(79,70,229,.35);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 28px rgba(79,70,229,.45);
        background: linear-gradient(135deg,#4f46e5,#4338ca);
    }

    .stButton > button::after {
        content: "";
        position: absolute;
        top: 50%;
        left: 50%;
        width: 8px;
        height: 8px;
        background: rgba(255,255,255,.5);
        border-radius: 50%;
        transform: translate(-50%,-50%) scale(0);
        opacity: 0;
    }

    .stButton > button:active::after {
        animation: ripple .6s ease-out;
    }

    @keyframes ripple {
        0% { transform: translate(-50%,-50%) scale(0); opacity:.6; }
        100% { transform: translate(-50%,-50%) scale(18); opacity:0; }
    }
    </style>
    """, unsafe_allow_html=True)

    # =========================================================
    st.markdown("## Study Matchmaking")
    ai_chat_ui()
    st.divider()

    # ================= MATCH SEARCH =================
    if not st.session_state.confirmed and not st.session_state.proposed_match:
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

        if st.button("Check compatible users"):
            best, score = find_best_match(current)
            if best:
                st.session_state.proposed_match = best
                st.session_state.proposed_score = score
                st.rerun()

        st.info("Click the button to find a compatible study partner.")
        return

    # ================= CONFIRMATION =================
    if st.session_state.proposed_match and not st.session_state.confirmed:
        u = st.session_state.proposed_match

        st.subheader("Confirm study partner")

        st.markdown(f"""
        <div style="border:1px solid #e5e7eb;border-radius:14px;
                    padding:16px;background:#ffffff">
            <b>{u['name']}</b><br>
            Grade: {u['grade']}<br>
            Time: {u['time']}<br>
            Strong subjects: {", ".join(u['strong'])}<br>
            Weak subjects: {", ".join(u['weak'])}<br>
            Compatibility score: {st.session_state.proposed_score}
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Confirm match"):
                match_id = f"{st.session_state.user_id}_{u['user_id']}_{now()}"

                conn.execute("""
                    UPDATE profiles SET status='matched', match_id=?
                    WHERE user_id IN (?,?)
                """, (match_id, st.session_state.user_id, u["user_id"]))

                conn.execute("""
                    INSERT INTO sessions(match_id, user1_id, user2_id, started_at)
                    VALUES (?,?,?,?)
                """, (match_id, st.session_state.user_id, u["user_id"], now()))

                conn.commit()
                st.session_state.current_match_id = match_id
                st.session_state.confirmed = True
                st.session_state.proposed_match = None
                st.balloons()
                st.rerun()

        with col2:
            if st.button("Find another"):
                st.session_state.proposed_match = None
                st.session_state.proposed_score = None
                st.rerun()

        return

    # ================= LIVE SESSION =================
    if should_poll():
        fetch_messages(st.session_state.current_match_id)
        poll()

    st.subheader("Live chat")
    for s, m in st.session_state.chat_log[-50:]:
        st.write(f"{s}: {m}")

    msg = st.text_input("Message")
    if st.button("Send") and msg:
        conn.execute("""
            INSERT INTO messages(match_id, sender, message, created_ts)
            VALUES (?,?,?,?)
        """, (st.session_state.current_match_id, st.session_state.user_name, msg, now()))
        conn.commit()
        st.rerun()

    f = st.file_uploader("Upload file")
    if f:
        path = f"{UPLOAD_DIR}/{st.session_state.current_match_id}_{f.name}"
        with open(path, "wb") as out:
            out.write(f.read())
        conn.execute("""
            INSERT INTO session_files(match_id, uploader, filename, filepath)
            VALUES (?,?,?,?)
        """, (st.session_state.current_match_id, st.session_state.user_name, f.name, path))
        conn.commit()
        st.success("File uploaded")

    if st.button("End session"):
        conn.execute(
            "UPDATE sessions SET ended_at=? WHERE match_id=?",
            (now(), st.session_state.current_match_id)
        )
        conn.commit()

        chat_text = "\n".join([m for _, m in st.session_state.chat_log])
        st.session_state.summary = ask_ai(
            "Summarize this study session in 5 bullet points:\n" + chat_text
        )
        st.session_state.quiz = ask_ai(
            "Create 3 MCQ questions based on this study session:\n" + chat_text
        )

        st.session_state.session_ended = True
        st.rerun()

    # ================= POST SESSION =================
    if st.session_state.session_ended:
        st.subheader("Session summary")
        st.write(st.session_state.summary)

        if not st.session_state.rating_given:
            rating = star_rating()
            if rating:
                conn.execute("""
                    INSERT INTO session_ratings(match_id, rater_id, rater_name, rating)
                    VALUES (?,?,?,?)
                """, (
                    st.session_state.current_match_id,
                    st.session_state.user_id,
                    st.session_state.user_name,
                    rating
                ))
                conn.commit()
                st.session_state.rating_given = True
                st.success("Rating saved")

        st.subheader("Session quiz")
        st.text(st.session_state.quiz)

        if st.button("Back to matchmaking"):
            reset_matchmaking()
