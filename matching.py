import streamlit as st
import os
import time
from database import cursor, conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads/sessions"
MATCH_THRESHOLD = 30

# =========================================================
# LOAD USERS
# =========================================================
def load_profiles():
    cursor.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects, p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id = p.user_id
        WHERE p.status = 'waiting'
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

# =========================================================
# MATCH LOGIC
# =========================================================
def score(u1, u2):
    s = 0
    s += len(set(u1["weak"]) & set(u2["strong"])) * 25
    s += len(set(u2["weak"]) & set(u1["strong"])) * 25
    if u1["grade"] == u2["grade"]:
        s += 10
    if u1["time"] == u2["time"]:
        s += 10
    return s

def find_best(current, users):
    best, best_s = None, 0
    for u in users:
        if u["user_id"] == current["user_id"]:
            continue
        sc = score(current, u)
        if sc > best_s:
            best, best_s = u, sc
    return (best, best_s) if best_s >= MATCH_THRESHOLD else (None, 0)

# =========================================================
# CHAT + FILE HELPERS
# =========================================================
def load_msgs(mid):
    cursor.execute(
        "SELECT sender, message FROM messages WHERE match_id=? ORDER BY id",
        (mid,)
    )
    return cursor.fetchall()

def send_msg(mid, sender, message):
    cursor.execute(
        "INSERT INTO messages (match_id, sender, message) VALUES (?, ?, ?)",
        (mid, sender, message)
    )
    conn.commit()

def save_file(mid, uploader, file):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = f"{UPLOAD_DIR}/{mid}_{file.name}"
    with open(path, "wb") as out:
        out.write(file.getbuffer())

    cursor.execute("""
        INSERT INTO session_files (match_id, uploader, filename, filepath)
        VALUES (?, ?, ?, ?)
    """, (mid, uploader, file.name, path))
    conn.commit()

def load_files(mid):
    cursor.execute("""
        SELECT uploader, filename, filepath
        FROM session_files
        WHERE match_id=?
        ORDER BY uploaded_at
    """, (mid,))
    return cursor.fetchall()

# =========================================================
# END SESSION
# =========================================================
def end_session(match_id):
    cursor.execute("""
        UPDATE profiles
        SET status='waiting', match_id=NULL
        WHERE match_id=?
    """, (match_id,))
    conn.commit()

# =========================================================
# AI QUIZ
# =========================================================
def generate_quiz_from_chat(match_id):
    messages = load_msgs(match_id)
    if not messages:
        return []

    chat_text = "\n".join([f"{s}: {m}" for s, m in messages])

    prompt = f"""
    Create exactly 3 MCQs from this discussion.

    Format:
    Q1. Question
    A) option
    B) option
    C) option
    D) option
    Answer: A

    Discussion:
    {chat_text}
    """

    response = ask_ai(prompt)
    questions = []

    blocks = response.split("Q")[1:]
    for b in blocks:
        lines = b.strip().split("\n")
        q = lines[0][2:].strip()
        opts, ans = {}, None

        for l in lines:
            if l.startswith(("A)", "B)", "C)", "D)")):
                opts[l[0]] = l[2:].strip()
            if "Answer:" in l:
                ans = l.split(":")[-1].strip()

        if opts and ans:
            questions.append({"question": q, "options": opts, "answer": ans})

    return questions

# =========================================================
# PRACTICE QUIZ UI
# =========================================================
def render_practice_quiz(match_id):
    st.markdown("## 🧠 Practice Quiz")

    if not st.session_state.quiz_questions:
        st.session_state.quiz_questions = generate_quiz_from_chat(match_id)
        st.session_state.quiz_answers = {}
        st.session_state.quiz_submitted = False

    if not st.session_state.quiz_questions:
        st.info("Not enough content for a quiz.")
        if st.button("Back to Matchmaking"):
            reset_to_matchmaking()
        return

    for i, q in enumerate(st.session_state.quiz_questions):
        st.markdown(f"**Q{i+1}. {q['question']}**")
        st.session_state.quiz_answers[i] = st.radio(
            "Choose",
            list(q["options"].keys()),
            format_func=lambda x: f"{x}) {q['options'][x]}",
            key=f"quiz_{i}"
        )

    if not st.session_state.quiz_submitted:
        if st.button("Submit Quiz", use_container_width=True):
            st.session_state.quiz_submitted = True

    if st.session_state.quiz_submitted:
        score = sum(
            1 for i, q in enumerate(st.session_state.quiz_questions)
            if st.session_state.quiz_answers.get(i) == q["answer"]
        )

        total = len(st.session_state.quiz_questions)
        st.metric("Score", f"{score}/{total}")

        if score == total:
            st.balloons()
        elif score == 0:
            st.error("All answers were incorrect.")
            st.snow()

        if st.button("Back to Matchmaking"):
            reset_to_matchmaking()

# =========================================================
# RESET
# =========================================================
def reset_to_matchmaking():
    for k in [
        "current_match_id", "partner", "partner_score",
        "session_ended", "celebrated", "rating",
        "show_summary", "show_practice",
        "quiz_questions", "quiz_answers", "quiz_submitted",
        "proposed_match", "proposed_score",
        "session_start_time"
    ]:
        st.session_state.pop(k, None)
    st.rerun()

# =========================================================
# MAIN PAGE (THIS WAS MISSING ❗)
# =========================================================
def matchmaking_page():

    # INIT STATE
    for k, v in {
        "current_match_id": None,
        "partner": None,
        "partner_score": None,
        "celebrated": False,
        "session_ended": False,
        "quiz_questions": [],
        "quiz_answers": {},
        "quiz_submitted": False
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    st.markdown("### 🤖 AI Study Assistant")
    with st.form("ai"):
        q = st.text_input("Ask a question")
        if st.form_submit_button("Ask") and q:
            st.success(ask_ai(q))

    st.divider()

    if not st.session_state.current_match_id:
        if st.button("Find Best Match", use_container_width=True):
            user = {
                "user_id": st.session_state.user_id,
                "name": st.session_state.user_name,
                "role": "",
                "grade": "",
                "time": "",
                "strong": [],
                "weak": []
            }
            m, s = find_best(user, load_profiles())
            if m:
                st.session_state.partner = m
                st.session_state.partner_score = s
                st.session_state.current_match_id = f"{user['user_id']}-{m['user_id']}-{int(time.time())}"
                st.session_state.session_start_time = time.time()
                st.rerun()
        return

    # LIVE SESSION
    match_id = st.session_state.current_match_id
    st.success(" ☆ You're matched!")
    st.balloons()

    st.markdown("### ◉ Chat")
    for s, m in load_msgs(match_id):
        st.markdown(f"**{s}:** {m}")

    with st.form("chat"):
        msg = st.text_input("Message")
        if st.form_submit_button("Send") and msg:
            send_msg(match_id, st.session_state.user_name, msg)
            st.rerun()

    if st.button("⚫️End Session", use_container_width=True):
        end_session(match_id)
        render_practice_quiz(match_id)
