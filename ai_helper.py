import streamlit as st
import google.generativeai as genai

# Setup Gemini in the helper file
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    model = None

def ask_ai(prompt):
    if model:
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI Error: {str(e)}"
    return "AI is not configured. Please add GEMINI_API_KEY to secrets."
