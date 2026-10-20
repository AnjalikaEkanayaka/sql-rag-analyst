from src.retrieval import retrieve

K = 4
CASES = [
    ("How many customers are there in each country?", {"Customer"}),
    ("List all albums by AC/DC", {"Album", "Artist"}),
    ("Which genre has the most tracks?", {"Genre", "Track"}),
    ("What is the total revenue per year?", {"Invoice"}),
    ("Which employee supports the most customers?", {"Employee", "Customer"}),
    ("Show the 5 longest tracks", {"Track"}),
    ("Which tracks are in the Classical playlist?", {"Playlist", "PlaylistTrack", "Track"}),
    ("Who is the best-selling artist?", {"Artist", "Album", "Track", "InvoiceLine"}),
    ("Find the manager of each employee", {"Employee"}),
    ("What are the top 3 customers by total spending?", {"Customer", "Invoice"}),
]

total = 0
for q, expected in CASES:
    got = [r["table"] for r in retrieve(q, k=K)]
    recall = len(expected & set(got)) / len(expected)
    total += recall
    print(f"{recall:.2f} | {q}\n       got:  {got}\n       want: {sorted(expected)}")
print(f"\nmean table recall@{K}: {total / len(CASES):.2f}")