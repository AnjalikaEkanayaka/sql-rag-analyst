"""Build the data dictionary: DB facts (auto) + plain-language meaning (written by us)."""
import json
import sqlite3
from pathlib import Path

DB = "file:data/chinook.db?mode=ro"
OUT_JSON = Path("data/data_dictionary.json")
OUT_MD = Path("data/data_dictionary.md")

# ---- Human-written meaning --------------------------------------------------
TABLES = {
    "Artist": "Music artists or bands. One artist can have many albums.",
    "Album": "Music albums. Each album belongs to one artist and contains many tracks.",
    "Track": "Individual songs sold in the store. Links to its album, genre and media type. The main product table.",
    "Genre": "Music genres such as Rock, Jazz, Metal. Lookup table for Track.GenreId.",
    "MediaType": "File formats of tracks, such as MPEG audio file. Lookup table for Track.MediaTypeId.",
    "Playlist": "Named playlists (for example 'Music', 'Classical'). Tracks are attached via PlaylistTrack.",
    "PlaylistTrack": "Bridge table linking playlists and tracks (many-to-many). Each row says track X is in playlist Y.",
    "Customer": "People who buy music from the store. Each has a country, city, email and an assigned support rep (an Employee).",
    "Employee": "Store staff. ReportsTo points to the employee's manager (self-reference). Support reps serve customers.",
    "Invoice": "One purchase (order) by one customer, with date, billing location and total amount.",
    "InvoiceLine": "One line item of an invoice: one track bought, with unit price and quantity. Revenue by track or genre comes from here.",
}

COLUMNS = {
    "Artist.ArtistId": "Unique artist ID.",
    "Artist.Name": "Artist or band name.",
    "Album.AlbumId": "Unique album ID.",
    "Album.Title": "Album title.",
    "Album.ArtistId": "The artist who made the album.",
    "Track.TrackId": "Unique track ID.",
    "Track.Name": "Song title.",
    "Track.AlbumId": "Album the track belongs to (can be NULL).",
    "Track.MediaTypeId": "File format of the track.",
    "Track.GenreId": "Genre of the track (can be NULL).",
    "Track.Composer": "Composer names, free text (often NULL).",
    "Track.Milliseconds": "Track length in milliseconds (divide by 1000 for seconds).",
    "Track.Bytes": "File size in bytes.",
    "Track.UnitPrice": "Price of one copy of the track in dollars.",
    "Genre.GenreId": "Unique genre ID.",
    "Genre.Name": "Genre name.",
    "MediaType.MediaTypeId": "Unique media type ID.",
    "MediaType.Name": "Media format name.",
    "Playlist.PlaylistId": "Unique playlist ID.",
    "Playlist.Name": "Playlist name.",
    "PlaylistTrack.PlaylistId": "Playlist containing the track.",
    "PlaylistTrack.TrackId": "Track inside the playlist.",
    "Customer.CustomerId": "Unique customer ID.",
    "Customer.FirstName": "Customer first name.",
    "Customer.LastName": "Customer last name.",
    "Customer.Company": "Customer's company (often NULL).",
    "Customer.Address": "Street address.",
    "Customer.City": "City.",
    "Customer.State": "State or province (often NULL outside the USA/Canada).",
    "Customer.Country": "Country name, e.g. 'USA', 'Brazil'.",
    "Customer.PostalCode": "Postal or ZIP code.",
    "Customer.Phone": "Phone number.",
    "Customer.Fax": "Fax number (often NULL).",
    "Customer.Email": "Email address.",
    "Customer.SupportRepId": "The Employee who supports this customer.",
    "Employee.EmployeeId": "Unique employee ID.",
    "Employee.LastName": "Employee last name.",
    "Employee.FirstName": "Employee first name.",
    "Employee.Title": "Job title, e.g. 'Sales Support Agent', 'General Manager'.",
    "Employee.ReportsTo": "EmployeeId of this employee's manager (NULL for the top boss).",
    "Employee.BirthDate": "Date of birth.",
    "Employee.HireDate": "Date hired.",
    "Employee.Address": "Street address.",
    "Employee.City": "City.",
    "Employee.State": "State or province.",
    "Employee.Country": "Country.",
    "Employee.PostalCode": "Postal code.",
    "Employee.Phone": "Phone number.",
    "Employee.Fax": "Fax number.",
    "Employee.Email": "Work email.",
    "Invoice.InvoiceId": "Unique invoice (order) ID.",
    "Invoice.CustomerId": "The customer who made the purchase.",
    "Invoice.InvoiceDate": "Date and time of the purchase.",
    "Invoice.BillingAddress": "Billing street address.",
    "Invoice.BillingCity": "Billing city.",
    "Invoice.BillingState": "Billing state or province.",
    "Invoice.BillingCountry": "Billing country, e.g. 'USA'.",
    "Invoice.BillingPostalCode": "Billing postal code.",
    "Invoice.Total": "Total amount of the invoice in dollars (sum of its lines).",
    "InvoiceLine.InvoiceLineId": "Unique line-item ID.",
    "InvoiceLine.InvoiceId": "The invoice this line belongs to.",
    "InvoiceLine.TrackId": "The track that was bought.",
    "InvoiceLine.UnitPrice": "Price per unit at purchase time.",
    "InvoiceLine.Quantity": "Number of copies bought.",
}


def main():
    con = sqlite3.connect(DB, uri=True)
    cur = con.cursor()
    names = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    dictionary = []
    for t in names:
        fks = {fk[3]: f"{fk[2]}.{fk[4]}" for fk in cur.execute(f'PRAGMA foreign_key_list("{t}")')}
        columns = []
        for _cid, col, ctype, _nn, _d, pk in cur.execute(f'PRAGMA table_info("{t}")').fetchall():
            rows = cur.execute(
                f'SELECT DISTINCT "{col}" FROM "{t}" WHERE "{col}" IS NOT NULL LIMIT 3').fetchall()
            columns.append({
                "name": col,
                "type": ctype,
                "primary_key": bool(pk),
                "foreign_key": fks.get(col),
                "description": COLUMNS.get(f"{t}.{col}", "MISSING DESCRIPTION"),
                "examples": [str(r[0])[:40] for r in rows],
            })
        dictionary.append({
            "table": t,
            "description": TABLES.get(t, "MISSING DESCRIPTION"),
            "row_count": cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0],
            "columns": columns,
        })

    OUT_JSON.write_text(json.dumps(dictionary, indent=2), encoding="utf-8")

    lines = ["# Chinook data dictionary\n"]
    for tb in dictionary:
        lines.append(f"## {tb['table']} ({tb['row_count']} rows)\n{tb['description']}\n")
        for c in tb["columns"]:
            tags = (" PK" if c["primary_key"] else "") + (f" FK->{c['foreign_key']}" if c["foreign_key"] else "")
            lines.append(f"- **{c['name']}** ({c['type']}{tags}): {c['description']} "
                         f"Examples: {', '.join(c['examples'])}")
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    missing = sum(1 for tb in dictionary for c in tb["columns"] if "MISSING" in c["description"])
    print(f"{len(dictionary)} tables, {sum(len(t['columns']) for t in dictionary)} columns, "
          f"{missing} missing descriptions")


if __name__ == "__main__":
    main()