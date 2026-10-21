from src.llm import get_llm
from src.pipeline import ask

QUESTIONS = [
    "How many customers are there in each country?",
    "List all albums by AC/DC",
    "Which genre has the most tracks?",
    "What are the top 3 customers by total spending?",
    "What is the total revenue per year?",
    "Who is the best-selling artist?",  # BONUS: join-bridge, may fail
]

for i, q in enumerate(QUESTIONS, 1):
    out = ask(q)
    print(f"\n[{i}] {q}\nTables: {out['tables']}\nSQL: {out['sql']}")
    print("Error:", out["error"])
    print("Rows:", out["rows"][:3])
    print("Explanation:", out["explanation"])

llm = get_llm()
print(f"\ncache hits={llm.hits} misses={llm.misses}")