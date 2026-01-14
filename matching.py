import streamlit as st
import os
import time
from database import cursor, conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads/sessions"

# =========================================================
# ENSURE RATINGS TABLE EXISTS
# =========================================================
cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT NOT NULL,
    rater_id INTEGER NOT NULL,
    rating INTEGER NOT NULL,
    created_at INTEGER NOT NULL
)
""")
conn.commit()

# =========================================================
# HELPERS
# =========================================================
def now():
    return int(time.time())

def update_last_seen():
    cursor.execute(
        "UPDATE profiles SET last_seen=? WHERE user_id=?",
        (now(), st.session_state.user_id)
    )
    conn.commit()

# =========================================================
# CHAT
# =========================================================
def load_msgs(mid):
    cursor.execute(
        "SELECT sender, message FROM messages WHERE match_id=? ORDER BY id",
        (mid,))
    return cursor.fetchall()

def send_msg(mid, sender, message):
    cursor.execute(
        "INSERT INTO messages (match_id, sender, message) VALUES (?,?,?)",
        (mid, sender, message))
    conn.commit()
    update_last_seen()

# =========================================================
# FILES
# =========================================================
def save_file(mid, uploader, file):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = f"{UPLOAD_DIR}/{mid}_{file.name}"
    with open(path, "wb") as f:
        f.write(file.getbuffer())

    cursor.execute("""
        INSERT INTO session_files (match_id, uploader, filename, filepath)
        VALUES (?,?,?,?)
    """, (mid, uploader, file.name, path))
    conn.commit()

def load_files(mid):
    cursor.execute("""
        SELECT uploader, filename, filepath
        FROM session_files WHERE match_id=?
    """, (mid,))
    return cursor.fetchall()

# =========================================================
# END SESSION
# =========================================================
def end_session(match_id):
    st.session_state.last_session_id = match_id

    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE match_id=?
    """, (match_id,))
    conn.commit()

    st.session_state.current_match_id = None
    st.session_state.session_ended = True

# =========================================================
# AI QUIZ
# =========================================================
def generate_quiz_from_chat(match_id):
    msgs = load_msgs(match_id)
    discussion = "\n".join([f"{s}: {m}" for s, m in msgs])

    raw = ask_ai(f"""
Create EXACTLY 3 MCQs from this discussion.
If discussion is short, create simple questions.

Discussion:
{discussion}
""")

    qs = []
    for b in raw.split("Q")[1:]:
        lines = b.splitlines()
        q = lines[0].split(".", 1)[-1]
        opts, ans = {}, None
        for l in lines:
            if l[:2] in ["A)", "B)", "C)", "D)"]:
                opts[l[0]] = l[2:].strip()
            if "Answer:" in l:
                ans = l.split(":")[-1].strip()
        if len(opts) == 4 and ans:
            qs.append({"question": q, "options": opts, "answer": ans})
    return qs[:3]

def render_practice_quiz(match_id):
    st.subheader("🧠 Practice Quiz")

    quiz = generate_quiz_from_chat(match_id)
    answers = {}

    for i, q in enumerate(quiz):
        st.markdown(f"**Q{i+1}. {q['question']}**")
        answers[i] = st.radio(
            "Choose",
            list(q["options"].keys()),
            format_func=lambda x: f"{x}) {q['options'][x]}",
            key=f"quiz_{i}"
        )

    if st.button("Submit Quiz"):
        score = sum(1 for i, q in enumerate(quiz) if answers.get(i) == q["answer"])
        st.metric("Score", f"{score}/3")
        if score == 3:
            st.balloons()

# =========================================================
# SESSION SUMMARY
# =========================================================
def render_session_summary(match_id):
    msgs = load_msgs(match_id)
    discussion = "\n".join([f"{s}: {m}" for s, m in msgs])

    summary = ask_ai(f"""
Summarize this study session:
- Topics discussed
- What was learned
- Suggestions for improvement

Discussion:
{discussion}
""")

    st.subheader("📝 Session Summary")
    st.write(summary)

# =========================================================
# MAIN PAGE
# =========================================================
def matchmaking_page():
    update_last_seen()

    st.session_state.setdefault("current_match_id", None)
    st.session_state.setdefault("session_ended", False)
    st.session_state.setdefault("last_session_id", None)
    st.session_state.setdefault("selected_rating", 0)

    # ================= LIVE SESSION =================
    if st.session_state.current_match_id and not st.session_state.session_ended:
        mid = st.session_state.current_match_id

        st.subheader("💬 Chat")
        for s, m in load_msgs(mid):
            st.markdown(f"**{s}:** {m}")

        with st.form("chat"):
            msg = st.text_input("Message")
            if st.form_submit_button("Send") and msg:
                send_msg(mid, st.session_state.user_name, msg)
                st.rerun()

        st.subheader("📁 Files")
        f = st.file_uploader("Upload")
        if f and st.button("Upload file"):
            save_file(mid, st.session_state.user_name, f)
            st.rerun()

        for u, n, p in load_files(mid):
            with open(p, "rb") as file:
                st.download_button(f"{n} ({u})", file)

        if st.button("End Session", use_container_width=True):
            end_session(mid)
        return

    # ================= POST SESSION =================
    if st.session_state.session_ended:
        sid = st.session_state.last_session_id

        st.subheader("⭐ Rate your partner")

        cols = st.columns(5)
        for i in range(5):
            if cols[i].button("⭐" if i < st.session_state.selected_rating else "☆", key=f"star_{i}"):
                st.session_state.selected_rating = i + 1

        if st.session_state.selected_rating > 0:
            st.info(f"You selected {st.session_state.selected_rating} star(s)")

        if st.button("Submit Rating") and st.session_state.selected_rating > 0:
            cursor.execute("""
                INSERT INTO ratings (match_id, rater_id, rating, created_at)
                VALUES (?,?,?,?)
            """, (
                sid,
                st.session_state.user_id,
                st.session_state.selected_rating,
                now()
            ))
            conn.commit()
            st.success("⭐ Rating submitted")

            render_session_summary(sid)
            render_practice_quiz(sid)
