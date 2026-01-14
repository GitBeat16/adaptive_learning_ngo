import streamlit as st
import os
import time
from database import cursor, conn
from ai_helper import ask_ai

UPLOAD_DIR = "uploads/sessions"
MATCH_THRESHOLD = 20
PARTNER_TIMEOUT = 60  # seconds

# =========================================================
# LOAD USERS
# =========================================================
def load_profiles():
    cursor.execute("""
        SELECT a.id, a.name, p.role, p.grade, p.time,
               p.strong_subjects, p.weak_subjects, p.teaches
        FROM profiles p
        JOIN auth_users a ON a.id = p.user_id
        WHERE p.status='waiting'
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
    best, best_s = None, -1
    for u in users:
        if u["user_id"] == current["user_id"]:
            continue
        sc = score(current, u)
        if sc > best_s:
            best, best_s = u, sc
    return (best, best_s) if best else (None, 0)

# =========================================================
# PRESENCE
# =========================================================
def update_last_seen():
    try:
        cursor.execute(
            "UPDATE profiles SET last_seen=? WHERE user_id=?",
            (int(time.time()), st.session_state.user_id)
        )
        conn.commit()
    except:
        pass

# =========================================================
# CHAT + FILE HELPERS
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
    update_last_seen()

def load_files(mid):
    cursor.execute("""
        SELECT uploader, filename, filepath
        FROM session_files
        WHERE match_id=?
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
    st.session_state.session_end = time.time()
    st.session_state.session_ended = True

# =========================================================
# AI QUIZ FROM CHAT
# =========================================================
def generate_quiz_from_chat(match_id):
    msgs = load_msgs(match_id)
    if not msgs:
        return []

    discussion = "\n".join([f"{s}: {m}" for s, m in msgs])

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
{discussion}
"""
    raw = ask_ai(prompt)
    questions = []

    for block in raw.split("Q")[1:]:
        lines = block.strip().split("\n")
        q = lines[0][2:].strip()
        opts, ans = {}, None

        for l in lines:
            if l[:2] in ["A)", "B)", "C)", "D)"]:
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
    st.markdown("## 🧠 Practice Quiz (AI Generated from Chat)")

    if "quiz_questions" not in st.session_state:
        st.session_state.quiz_questions = generate_quiz_from_chat(match_id)
        st.session_state.quiz_answers = {}
        st.session_state.quiz_submitted = False

    if not st.session_state.quiz_questions:
        st.info("Not enough discussion to generate quiz.")
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
            st.error("All answers incorrect")
            st.snow()

        if st.button("Back to Matchmaking"):
            reset_to_matchmaking()

# =========================================================
# RESET
# =========================================================
def reset_to_matchmaking():
    for k in [
        "current_match_id", "partner", "partner_score",
        "session_start", "session_end", "session_ended",
        "quiz_questions", "quiz_answers", "quiz_submitted",
        "rating", "proposed_match", "proposed_score",
        "show_practice"
    ]:
        st.session_state.pop(k, None)
    st.rerun()

# =========================================================
# PAGE
# =========================================================
def matchmaking_page():

    update_last_seen()

    for k, v in {
        "current_match_id": None,
        "session_ended": False,
        "show_practice": False
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # -----------------------------------------------------
    # DB SYNC
    cursor.execute("SELECT match_id FROM profiles WHERE user_id=?", (st.session_state.user_id,))
    db_match = cursor.fetchone()

    if db_match and db_match[0]:
        st.session_state.current_match_id = db_match[0]
        if "session_start" not in st.session_state:
            st.session_state.session_start = time.time()

    # -----------------------------------------------------
    # LIVE SESSION
    if st.session_state.current_match_id and not st.session_state.session_ended:
        match_id = st.session_state.current_match_id

        st.success("🎉 Live session in progress")
        elapsed = int(time.time() - st.session_state.session_start)
        st.caption(f"⏱ {elapsed//60}m {elapsed%60}s")

        st.markdown("### 💬 Live Chat")
        for s, m in load_msgs(match_id):
            st.markdown(f"**{s}:** {m}")

        with st.form("chat"):
            msg = st.text_input("Message")
            if st.form_submit_button("Send") and msg:
                send_msg(match_id, st.session_state.user_name, msg)
                st.rerun()

        st.divider()

        st.markdown("### 📂 Shared Files")
        with st.form("file_form"):
            f = st.file_uploader("Upload file")
            if st.form_submit_button("Upload") and f:
                save_file(match_id, st.session_state.user_name, f)
                st.rerun()

        for u, n, p in load_files(match_id):
            with open(p, "rb") as file:
                st.download_button(n, file, use_container_width=True)

        if st.button("🔴 End Session", use_container_width=True):
            end_session(match_id)

        return

    # -----------------------------------------------------
    # POST SESSION OPTIONS
    if st.session_state.session_ended:
        st.markdown("## ✅ Session Completed")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🧠 Practice on this topic"):
                st.session_state.show_practice = True

        with col2:
            if st.button("🔁 Skip → Matchmaking"):
                reset_to_matchmaking()

        if st.session_state.show_practice:
            render_practice_quiz(st.session_state.current_match_id)
