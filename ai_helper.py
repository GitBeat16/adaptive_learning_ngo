from openai import OpenAI
import os

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def ask_ai(question, grade=None):
    system_prompt = "You are a helpful tutor explaining concepts simply."

    if grade:
        system_prompt += f" Explain at a grade {grade} level."

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        max_tokens=300,
        temperature=0.4
    )

    return response.choices[0].message.content.strip()
