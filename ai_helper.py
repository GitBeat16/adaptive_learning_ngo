import streamlit as st
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def ask_ai(question: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful tutor for students."},
            {"role": "user", "content": question}
        ],
        max_tokens=300,
        temperature=0.4
    )
    return response.choices[0].message.content.strip()
