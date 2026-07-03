from normalize import normalize_resume

with open("debug.txt", "r", encoding="utf-8") as f:
    text = f.read()

print(normalize_resume(text))


