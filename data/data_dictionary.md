# Chinook data dictionary

## Album (347 rows)
Music albums. Each album belongs to one artist and contains many tracks.

- **AlbumId** (INTEGER PK): Unique album ID. Examples: 1, 4, 2
- **Title** (NVARCHAR(160)): Album title. Examples: For Those About To Rock We Salute You, Balls to the Wall, Restless and Wild
- **ArtistId** (INTEGER FK->Artist.ArtistId): The artist who made the album. Examples: 1, 2, 3

## Artist (275 rows)
Music artists or bands. One artist can have many albums.

- **ArtistId** (INTEGER PK): Unique artist ID. Examples: 1, 2, 3
- **Name** (NVARCHAR(120)): Artist or band name. Examples: AC/DC, Accept, Aerosmith

## Customer (59 rows)
People who buy music from the store. Each has a country, city, email and an assigned support rep (an Employee).

- **CustomerId** (INTEGER PK): Unique customer ID. Examples: 1, 3, 12
- **FirstName** (NVARCHAR(40)): Customer first name. Examples: Luís, Leonie, François
- **LastName** (NVARCHAR(20)): Customer last name. Examples: Gonçalves, Köhler, Tremblay
- **Company** (NVARCHAR(80)): Customer's company (often NULL). Examples: Embraer - Empresa Brasileira de Aeronáut, JetBrains s.r.o., Woodstock Discos
- **Address** (NVARCHAR(70)): Street address. Examples: Av. Brigadeiro Faria Lima, 2170, Theodor-Heuss-Straße 34, 1498 rue Bélanger
- **City** (NVARCHAR(40)): City. Examples: São José dos Campos, Stuttgart, Montréal
- **State** (NVARCHAR(40)): State or province (often NULL outside the USA/Canada). Examples: SP, QC, RJ
- **Country** (NVARCHAR(40)): Country name, e.g. 'USA', 'Brazil'. Examples: Brazil, Germany, Canada
- **PostalCode** (NVARCHAR(10)): Postal or ZIP code. Examples: 12227-000, 70174, H2G 1A7
- **Phone** (NVARCHAR(24)): Phone number. Examples: +55 (12) 3923-5555, +49 0711 2842222, +1 (514) 721-4711
- **Fax** (NVARCHAR(24)): Fax number (often NULL). Examples: +55 (12) 3923-5566, +420 2 4172 5555, +55 (11) 3033-4564
- **Email** (NVARCHAR(60)): Email address. Examples: luisg@embraer.com.br, leonekohler@surfeu.de, ftremblay@gmail.com
- **SupportRepId** (INTEGER FK->Employee.EmployeeId): The Employee who supports this customer. Examples: 3, 4, 5

## Employee (8 rows)
Store staff. ReportsTo points to the employee's manager (self-reference). Support reps serve customers.

- **EmployeeId** (INTEGER PK): Unique employee ID. Examples: 1, 2, 6
- **LastName** (NVARCHAR(20)): Employee last name. Examples: Adams, Edwards, Peacock
- **FirstName** (NVARCHAR(20)): Employee first name. Examples: Andrew, Nancy, Jane
- **Title** (NVARCHAR(30)): Job title, e.g. 'Sales Support Agent', 'General Manager'. Examples: General Manager, Sales Manager, Sales Support Agent
- **ReportsTo** (INTEGER FK->Employee.EmployeeId): EmployeeId of this employee's manager (NULL for the top boss). Examples: 1, 2, 6
- **BirthDate** (DATETIME): Date of birth. Examples: 1962-02-18 00:00:00, 1958-12-08 00:00:00, 1973-08-29 00:00:00
- **HireDate** (DATETIME): Date hired. Examples: 2002-08-14 00:00:00, 2002-05-01 00:00:00, 2002-04-01 00:00:00
- **Address** (NVARCHAR(70)): Street address. Examples: 11120 Jasper Ave NW, 825 8 Ave SW, 1111 6 Ave SW
- **City** (NVARCHAR(40)): City. Examples: Edmonton, Calgary, Lethbridge
- **State** (NVARCHAR(40)): State or province. Examples: AB
- **Country** (NVARCHAR(40)): Country. Examples: Canada
- **PostalCode** (NVARCHAR(10)): Postal code. Examples: T5K 2N1, T2P 2T3, T2P 5M5
- **Phone** (NVARCHAR(24)): Phone number. Examples: +1 (780) 428-9482, +1 (403) 262-3443, +1 (403) 263-4423
- **Fax** (NVARCHAR(24)): Fax number. Examples: +1 (780) 428-3457, +1 (403) 262-3322, +1 (403) 262-6712
- **Email** (NVARCHAR(60)): Work email. Examples: andrew@chinookcorp.com, nancy@chinookcorp.com, jane@chinookcorp.com

## Genre (25 rows)
Music genres such as Rock, Jazz, Metal. Lookup table for Track.GenreId.

- **GenreId** (INTEGER PK): Unique genre ID. Examples: 1, 2, 3
- **Name** (NVARCHAR(120)): Genre name. Examples: Rock, Jazz, Metal

## Invoice (412 rows)
One purchase (order) by one customer, with date, billing location and total amount.

- **InvoiceId** (INTEGER PK): Unique invoice (order) ID. Examples: 98, 121, 143
- **CustomerId** (INTEGER FK->Customer.CustomerId): The customer who made the purchase. Examples: 1, 2, 3
- **InvoiceDate** (DATETIME): Date and time of the purchase. Examples: 2021-01-01 00:00:00, 2021-01-02 00:00:00, 2021-01-03 00:00:00
- **BillingAddress** (NVARCHAR(70)): Billing street address. Examples: Theodor-Heuss-Straße 34, Ullevålsveien 14, Grétrystraat 63
- **BillingCity** (NVARCHAR(40)): Billing city. Examples: Stuttgart, Oslo, Brussels
- **BillingState** (NVARCHAR(40)): Billing state or province. Examples: AB, MA, Dublin
- **BillingCountry** (NVARCHAR(40)): Billing country, e.g. 'USA'. Examples: Germany, Norway, Belgium
- **BillingPostalCode** (NVARCHAR(10)): Billing postal code. Examples: 70174, 0171, 1000
- **Total** (NUMERIC(10,2)): Total amount of the invoice in dollars (sum of its lines). Examples: 1.98, 3.96, 5.94

## InvoiceLine (2240 rows)
One line item of an invoice: one track bought, with unit price and quantity. Revenue by track or genre comes from here.

- **InvoiceLineId** (INTEGER PK): Unique line-item ID. Examples: 579, 1, 1154
- **InvoiceId** (INTEGER FK->Invoice.InvoiceId): The invoice this line belongs to. Examples: 1, 2, 3
- **TrackId** (INTEGER FK->Track.TrackId): The track that was bought. Examples: 1, 2, 3
- **UnitPrice** (NUMERIC(10,2)): Price per unit at purchase time. Examples: 0.99, 1.99
- **Quantity** (INTEGER): Number of copies bought. Examples: 1

## MediaType (5 rows)
File formats of tracks, such as MPEG audio file. Lookup table for Track.MediaTypeId.

- **MediaTypeId** (INTEGER PK): Unique media type ID. Examples: 1, 2, 3
- **Name** (NVARCHAR(120)): Media format name. Examples: MPEG audio file, Protected AAC audio file, Protected MPEG-4 video file

## Playlist (18 rows)
Named playlists (for example 'Music', 'Classical'). Tracks are attached via PlaylistTrack.

- **PlaylistId** (INTEGER PK): Unique playlist ID. Examples: 1, 2, 3
- **Name** (NVARCHAR(120)): Playlist name. Examples: Music, Movies, TV Shows

## PlaylistTrack (8715 rows)
Bridge table linking playlists and tracks (many-to-many). Each row says track X is in playlist Y.

- **PlaylistId** (INTEGER PK FK->Playlist.PlaylistId): Playlist containing the track. Examples: 1, 3, 5
- **TrackId** (INTEGER PK FK->Track.TrackId): Track inside the playlist. Examples: 1, 2, 3

## Track (3503 rows)
Individual songs sold in the store. Links to its album, genre and media type. The main product table.

- **TrackId** (INTEGER PK): Unique track ID. Examples: 1, 6, 7
- **Name** (NVARCHAR(200)): Song title. Examples: For Those About To Rock (We Salute You), Balls to the Wall, Fast As a Shark
- **AlbumId** (INTEGER FK->Album.AlbumId): Album the track belongs to (can be NULL). Examples: 1, 2, 3
- **MediaTypeId** (INTEGER FK->MediaType.MediaTypeId): File format of the track. Examples: 1, 2, 3
- **GenreId** (INTEGER FK->Genre.GenreId): Genre of the track (can be NULL). Examples: 1, 2, 3
- **Composer** (NVARCHAR(220)): Composer names, free text (often NULL). Examples: Angus Young, Malcolm Young, Brian Johnso, U. Dirkschneider, W. Hoffmann, H. Frank,, F. Baltes, S. Kaufman, U. Dirkscneider &
- **Milliseconds** (INTEGER): Track length in milliseconds (divide by 1000 for seconds). Examples: 343719, 342562, 230619
- **Bytes** (INTEGER): File size in bytes. Examples: 11170334, 5510424, 3990994
- **UnitPrice** (NUMERIC(10,2)): Price of one copy of the track in dollars. Examples: 0.99, 1.99
