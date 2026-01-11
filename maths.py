import random

def generate_maths_question(grade):
    if grade <= 2:
        a, b = random.randint(1, 10), random.randint(1, 10)
        question = f"{a} + {b} = ?"
        answer = a + b

    elif grade <= 4:
        a, b = random.randint(10, 50), random.randint(1, 10)
        question = f"{a} - {b} = ?"
        answer = a - b

    elif grade <= 6:
        a, b = random.randint(2, 12), random.randint(2, 10)
        question = f"{a} × {b} = ?"
        answer = a * b

    elif grade <= 8:
        b = random.randint(2, 10)
        answer = random.randint(2, 10)
        a = b * answer
        question = f"{a} ÷ {b} = ?"

    else:
        a = random.randint(1, 10)
        question = f"{a}² = ?"
        answer = a * a

    options = list(set([
        answer,
        answer + random.randint(1, 5),
        answer - random.randint(1, 5),
        answer + random.randint(6, 10)
    ]))

    options = [o for o in options if o >= 0]
    random.shuffle(options)

    return {
        "q": question,
        "options": [str(o) for o in options[:4]],
        "answer": str(answer)
    }
