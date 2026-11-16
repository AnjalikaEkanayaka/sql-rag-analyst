window.DEMO = {
 "examples": [
  {
   "id": 17,
   "difficulty": "medium",
   "question": "How many tracks does each genre have? Show the genre name and the track count.",
   "status": "correct",
   "tables": [
    "Genre",
    "Track",
    "Playlist",
    "PlaylistTrack"
   ],
   "sql": "SELECT g.Name AS GenreName, COUNT(t.TrackId) AS TrackCount FROM Genre AS g LEFT JOIN Track AS t ON g.GenreId = t.GenreId GROUP BY g.GenreId, g.Name LIMIT 50",
   "error": null,
   "columns": [
    "GenreName",
    "TrackCount"
   ],
   "rows": [
    [
     "Rock",
     1297
    ],
    [
     "Jazz",
     130
    ],
    [
     "Metal",
     374
    ],
    [
     "Alternative & Punk",
     332
    ],
    [
     "Rock And Roll",
     12
    ],
    [
     "Blues",
     81
    ],
    [
     "Latin",
     579
    ],
    [
     "Reggae",
     58
    ],
    [
     "Pop",
     48
    ],
    [
     "Soundtrack",
     43
    ],
    [
     "Bossa Nova",
     15
    ],
    [
     "Easy Listening",
     24
    ]
   ],
   "row_count": 25,
   "explanation": "The query lists each music genre and how many tracks belong to it. For example, “Rock” has 1,297 tracks, “Jazz” 130, “Metal” 374, and so on. The result set contains 25 genres (more than the 10 shown).",
   "gold_sql": "SELECT g.Name, COUNT(*) FROM Track t JOIN Genre g ON t.GenreId = g.GenreId GROUP BY g.GenreId",
   "gold_tables": [
    "Genre",
    "Track"
   ]
  },
  {
   "id": 18,
   "difficulty": "medium",
   "question": "Who are the top 5 customers by total spending? Show first name, last name and total spent.",
   "status": "correct",
   "tables": [
    "Customer",
    "Employee",
    "Invoice"
   ],
   "sql": "SELECT c.FirstName, c.LastName, SUM(i.Total) AS TotalSpent FROM Customer AS c JOIN Invoice AS i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId, c.FirstName, c.LastName ORDER BY TotalSpent DESC LIMIT 5",
   "error": null,
   "columns": [
    "FirstName",
    "LastName",
    "TotalSpent"
   ],
   "rows": [
    [
     "Helena",
     "Holý",
     49.62
    ],
    [
     "Richard",
     "Cunningham",
     47.62
    ],
    [
     "Luis",
     "Rojas",
     46.62
    ],
    [
     "Ladislav",
     "Kovács",
     45.62
    ],
    [
     "Hugh",
     "O'Reilly",
     45.62
    ]
   ],
   "row_count": 5,
   "explanation": "The five customers who spent the most are:\n\n1. Helena Holý – $49.62  \n2. Richard Cunningham – $47.62  \n3. Luis Rojas – $46.62  \n4. Ladislav Kovács – $45.62  \n5. Hugh O'Reilly – $45.62",
   "gold_sql": "SELECT c.FirstName, c.LastName, ROUND(SUM(i.Total), 2) AS spent FROM Customer c JOIN Invoice i ON c.CustomerId = i.CustomerId GROUP BY c.CustomerId ORDER BY spent DESC LIMIT 5",
   "gold_tables": [
    "Customer",
    "Invoice"
   ]
  },
  {
   "id": 19,
   "difficulty": "medium",
   "question": "What is the total revenue for each year? Show the year and the revenue.",
   "status": "correct",
   "tables": [
    "InvoiceLine",
    "Invoice",
    "Customer",
    "Track"
   ],
   "sql": "SELECT STRFTIME('%Y', InvoiceDate) AS year, SUM(Total) AS revenue FROM Invoice GROUP BY year ORDER BY year LIMIT 50",
   "error": null,
   "columns": [
    "year",
    "revenue"
   ],
   "rows": [
    [
     "2021",
     449.46
    ],
    [
     "2022",
     481.45
    ],
    [
     "2023",
     469.58
    ],
    [
     "2024",
     477.53
    ],
    [
     "2025",
     450.58
    ]
   ],
   "row_count": 5,
   "explanation": "The total revenue for each year is:\n\n- 2021: $449.46  \n- 2022: $481.45  \n- 2023: $469.58  \n- 2024: $477.53  \n- 2025: $450.58  \n\n(These are the only years returned by the query.)",
   "gold_sql": "SELECT strftime('%Y', InvoiceDate) AS yr, ROUND(SUM(Total), 2) FROM Invoice GROUP BY yr",
   "gold_tables": [
    "Invoice"
   ]
  },
  {
   "id": 25,
   "difficulty": "medium",
   "question": "Which employees report to Nancy Edwards? Show their first and last names.",
   "status": "correct",
   "tables": [
    "Employee",
    "Customer",
    "Invoice",
    "Artist"
   ],
   "sql": "SELECT FirstName, LastName FROM Employee WHERE ReportsTo = (SELECT EmployeeId FROM Employee WHERE FirstName = 'Nancy' AND LastName = 'Edwards') LIMIT 50",
   "error": null,
   "columns": [
    "FirstName",
    "LastName"
   ],
   "rows": [
    [
     "Jane",
     "Peacock"
    ],
    [
     "Margaret",
     "Park"
    ],
    [
     "Steve",
     "Johnson"
    ]
   ],
   "row_count": 3,
   "explanation": "Three employees report to Nancy Edwards: Jane Peacock, Margaret Park, and Steve Johnson.",
   "gold_sql": "SELECT e.FirstName, e.LastName FROM Employee e JOIN Employee m ON e.ReportsTo = m.EmployeeId WHERE m.FirstName = 'Nancy' AND m.LastName = 'Edwards'",
   "gold_tables": [
    "Employee"
   ]
  },
  {
   "id": 31,
   "difficulty": "hard",
   "question": "Who is the best-selling artist by revenue? Show the artist name and the total revenue.",
   "status": "correct",
   "tables": [
    "Artist",
    "Track",
    "Album",
    "InvoiceLine"
   ],
   "sql": "SELECT a.Name AS ArtistName, SUM(il.UnitPrice * il.Quantity) AS TotalRevenue FROM Artist AS a JOIN Album AS al ON a.ArtistId = al.ArtistId JOIN Track AS t ON al.AlbumId = t.AlbumId JOIN InvoiceLine AS il ON t.TrackId = il.TrackId GROUP BY a.ArtistId, a.Name ORDER BY TotalRevenue DESC LIMIT 1",
   "error": null,
   "columns": [
    "ArtistName",
    "TotalRevenue"
   ],
   "rows": [
    [
     "Iron Maiden",
     138.6
    ]
   ],
   "row_count": 1,
   "explanation": "The query shows that **Iron Maiden** is the top‑earning artist, generating a total revenue of **$138.60**.",
   "gold_sql": "SELECT ar.Name, ROUND(SUM(il.UnitPrice * il.Quantity), 2) AS rev FROM InvoiceLine il JOIN Track t ON t.TrackId = il.TrackId JOIN Album al ON al.AlbumId = t.AlbumId JOIN Artist ar ON ar.ArtistId = al.ArtistId GROUP BY ar.ArtistId ORDER BY rev DESC LIMIT 1",
   "gold_tables": [
    "Album",
    "Artist",
    "InvoiceLine",
    "Track"
   ]
  },
  {
   "id": 36,
   "difficulty": "hard",
   "question": "Which customers have bought at least one Jazz track? Show their first and last names.",
   "status": "correct",
   "tables": [
    "Customer",
    "Track",
    "Artist",
    "InvoiceLine"
   ],
   "sql": "SELECT DISTINCT c.FirstName, c.LastName FROM Customer AS c JOIN Invoice AS i ON c.CustomerId = i.CustomerId JOIN InvoiceLine AS il ON i.InvoiceId = il.InvoiceId JOIN Track AS t ON il.TrackId = t.TrackId JOIN Genre AS g ON t.GenreId = g.GenreId WHERE g.Name = 'Jazz' LIMIT 50",
   "error": null,
   "columns": [
    "FirstName",
    "LastName"
   ],
   "rows": [
    [
     "Mark",
     "Philips"
    ],
    [
     "John",
     "Gordon"
    ],
    [
     "Frank",
     "Harris"
    ],
    [
     "Jack",
     "Smith"
    ],
    [
     "Tim",
     "Goyer"
    ],
    [
     "Dominique",
     "Lefebvre"
    ],
    [
     "Kathy",
     "Chase"
    ],
    [
     "Stanisław",
     "Wójcik"
    ],
    [
     "Phil",
     "Hughes"
    ],
    [
     "François",
     "Tremblay"
    ],
    [
     "František",
     "Wichterlová"
    ],
    [
     "Dan",
     "Miller"
    ]
   ],
   "row_count": 32,
   "explanation": "The query lists customers who have purchased at least one Jazz track, showing their first and last names. The result set contains 32 customers, and the first 10 shown are: Mark Philips, John Gordon, Frank Harris, Jack Smith, Tim Goyer, Dominique Lefebvre, Kathy Chase, Stanisław Wójcik, Phil Hughes, and François Tremblay.",
   "gold_sql": "SELECT DISTINCT c.FirstName, c.LastName FROM Customer c JOIN Invoice i ON i.CustomerId = c.CustomerId JOIN InvoiceLine il ON il.InvoiceId = i.InvoiceId JOIN Track t ON t.TrackId = il.TrackId JOIN Genre g ON g.GenreId = t.GenreId WHERE g.Name = 'Jazz'",
   "gold_tables": [
    "Customer",
    "Genre",
    "Invoice",
    "InvoiceLine",
    "Track"
   ]
  },
  {
   "id": 37,
   "difficulty": "hard",
   "question": "What percentage of the total revenue comes from invoices billed to the USA? Round to 2 decimal places.",
   "status": "correct",
   "tables": [
    "Invoice",
    "InvoiceLine",
    "Customer",
    "Employee"
   ],
   "sql": "SELECT ROUND(100.0 * SUM(CASE WHEN BillingCountry = 'USA' THEN Total ELSE 0 END) / SUM(Total), 2) AS USA_Revenue_Percentage FROM Invoice LIMIT 50",
   "error": null,
   "columns": [
    "USA_Revenue_Percentage"
   ],
   "rows": [
    [
     22.46
    ]
   ],
   "row_count": 1,
   "explanation": "About 22.46 % of the total revenue comes from invoices billed to the USA.",
   "gold_sql": "SELECT ROUND(100.0 * (SELECT SUM(Total) FROM Invoice WHERE BillingCountry = 'USA') / (SELECT SUM(Total) FROM Invoice), 2)",
   "gold_tables": [
    "Invoice"
   ]
  },
  {
   "id": 39,
   "difficulty": "hard",
   "question": "Which playlists contain at least one track by AC/DC? Show the playlist names without duplicates.",
   "status": "wrong_result",
   "tables": [
    "Playlist",
    "PlaylistTrack",
    "Genre",
    "Track"
   ],
   "sql": "SELECT DISTINCT p.Name FROM Playlist AS p JOIN PlaylistTrack AS pt ON p.PlaylistId = pt.PlaylistId JOIN Track AS t ON pt.TrackId = t.TrackId WHERE t.Composer LIKE '%AC/DC%' LIMIT 50",
   "error": null,
   "columns": [
    "Name"
   ],
   "rows": [
    [
     "Music"
    ]
   ],
   "row_count": 1,
   "explanation": "The query found one playlist that includes an AC/DC track: **“Music.”**",
   "gold_sql": "SELECT DISTINCT p.Name FROM Playlist p JOIN PlaylistTrack pt ON pt.PlaylistId = p.PlaylistId JOIN Track t ON t.TrackId = pt.TrackId JOIN Album al ON al.AlbumId = t.AlbumId JOIN Artist ar ON ar.ArtistId = al.ArtistId WHERE ar.Name = 'AC/DC'",
   "gold_tables": [
    "Album",
    "Artist",
    "Playlist",
    "PlaylistTrack",
    "Track"
   ]
  }
 ],
 "results": [
  {
   "name": "baseline-retrieval",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "dense only, n_chunks=10"
  },
  {
   "name": "baseline",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "97.5%",
   "easy": "100.0%",
   "medium": "100.0%",
   "hard": "90.0%",
   "notes": "dense k=4, schema-only prompt, explain off"
  },
  {
   "name": "ret-dense-k1",
   "k": "1",
   "n": "40",
   "recall": "0.650",
   "hit_all": "0.425",
   "mrr": "0.975",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "dense, n_chunks=10"
  },
  {
   "name": "ret-dense-k2",
   "k": "2",
   "n": "40",
   "recall": "0.834",
   "hit_all": "0.675",
   "mrr": "0.988",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "dense, n_chunks=10"
  },
  {
   "name": "ret-dense-k3",
   "k": "3",
   "n": "40",
   "recall": "0.929",
   "hit_all": "0.825",
   "mrr": "0.988",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "dense, n_chunks=10"
  },
  {
   "name": "ret-dense-k5",
   "k": "5",
   "n": "40",
   "recall": "0.980",
   "hit_all": "0.925",
   "mrr": "0.988",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "dense, n_chunks=10"
  },
  {
   "name": "ret-dense-k6",
   "k": "6",
   "n": "40",
   "recall": "0.990",
   "hit_all": "0.975",
   "mrr": "0.988",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "dense, n_chunks=10"
  },
  {
   "name": "ret-dense-k4-n28",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "dense, n_chunks=28"
  },
  {
   "name": "ret-bm25-k4",
   "k": "4",
   "n": "40",
   "recall": "0.884",
   "hit_all": "0.750",
   "mrr": "0.821",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "bm25, n_chunks=10"
  },
  {
   "name": "ret-hybrid-k4",
   "k": "4",
   "n": "40",
   "recall": "0.967",
   "hit_all": "0.900",
   "mrr": "0.963",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "hybrid, n_chunks=10"
  },
  {
   "name": "ret-hybrid-k4-n28",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.963",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "hybrid, n_chunks=28"
  },
  {
   "name": "ret-dense-k4-fk0.8",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "dense, n_chunks=10, fk-expand boost=0.8"
  },
  {
   "name": "ret-hybrid-k4-n28-fk0.95",
   "k": "4",
   "n": "40",
   "recall": "0.970",
   "hit_all": "0.925",
   "mrr": "0.963",
   "exec_acc": "-",
   "easy": "-",
   "medium": "-",
   "hard": "-",
   "notes": "hybrid, n_chunks=28, fk-expand boost=0.95"
  },
  {
   "name": "gen-strict-k4",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "90.0%",
   "easy": "100.0%",
   "medium": "93.3%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, strict tables, ~1800 prompt chars"
  },
  {
   "name": "gen-noschema",
   "k": "4",
   "n": "40",
   "recall": "-",
   "hit_all": "-",
   "mrr": "-",
   "exec_acc": "55.0%",
   "easy": "20.0%",
   "medium": "86.7%",
   "hard": "60.0%",
   "notes": "dense, n_chunks=10, NO schema, ~470 prompt chars"
  },
  {
   "name": "gen-nofk-k4",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, ~1660 prompt chars"
  },
  {
   "name": "gen-k2",
   "k": "2",
   "n": "40",
   "recall": "0.834",
   "hit_all": "0.675",
   "mrr": "0.988",
   "exec_acc": "82.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "50.0%",
   "notes": "dense, n_chunks=10, ~1217 prompt chars"
  },
  {
   "name": "gen-strict-k2",
   "k": "2",
   "n": "40",
   "recall": "0.834",
   "hit_all": "0.675",
   "mrr": "0.988",
   "exec_acc": "65.0%",
   "easy": "100.0%",
   "medium": "53.3%",
   "hard": "30.0%",
   "notes": "dense, n_chunks=10, strict tables, ~1217 prompt chars"
  },
  {
   "name": "gen-strict-nofk-k4",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, strict tables, ~1660 prompt chars"
  },
  {
   "name": "gen-retry1",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, strict tables, retries=1, ~1660 prompt chars, 2 retry calls"
  },
  {
   "name": "gen-coldesc",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, strict tables, col descriptions, ~2465 prompt chars"
  },
  {
   "name": "gen-examples",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, strict tables, example values, ~2721 prompt chars"
  },
  {
   "name": "gen-fewshot",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, strict tables, few-shot, ~2336 prompt chars"
  },
  {
   "name": "gen-retry1",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, strict tables, retries=1, ~1660 prompt chars, 2 retry calls"
  },
  {
   "name": "gen-coldesc",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, strict tables, col descriptions, ~2465 prompt chars"
  },
  {
   "name": "gen-examples",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, strict tables, example values, ~2721 prompt chars"
  },
  {
   "name": "gen-fewshot",
   "k": "4",
   "n": "40",
   "recall": "0.962",
   "hit_all": "0.900",
   "mrr": "0.988",
   "exec_acc": "87.5%",
   "easy": "100.0%",
   "medium": "86.7%",
   "hard": "70.0%",
   "notes": "dense, n_chunks=10, no FK hints, strict tables, few-shot, ~2336 prompt chars"
  }
 ],
 "model": "openai/gpt-oss-20b",
 "settings": "k=4 retrieved tables, foreign-key hints on, all known tables allowed"
};
