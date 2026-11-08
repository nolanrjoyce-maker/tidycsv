# tidycsv

Clean a messy CSV export in one command. One Python file, standard library only.

```bash
python3 tidycsv.py example_messy.csv --snake --report
python3 tidycsv.py export.csv -o clean.xlsx      # .xlsx output needs: pip install openpyxl
```

## What it fixes

It detects each column's type from its values (a column is converted only when at least 80% of its cells match) and then:

| Problem | Before | After |
|---|---|---|
| Mixed date formats | `11/02/2026`, `2026/11/04`, `11-03-2026` | `2026-11-02`, `2026-11-04`, `2026-11-03` |
| Money as text | `"$1,250.50"`, `(45.10)`, `1.200,50 EUR` | `1250.50`, `-45.10`, `1200.50` |
| US phone numbers | `555.123.4567`, `5550001111` | `(555) 123-4567`, `(555) 000-1111` |
| E-mail case | `JANE@EXAMPLE.COM` | `jane@example.com` |
| Whitespace and stray quotes | `  BOB WILSON  ` | `BOB WILSON` |
| Exact duplicate rows | two copies | one copy |
| Repeated or blank headers | `Name, Name, ` | `name, name_2, column_3` |

It also auto-detects the delimiter (`,` `;` tab `|`) and the encoding (UTF-8, Windows-1252, Latin-1).

`--report` prints each column's detected type and how many cells changed, so nothing changes silently:

```
rows: 6 in, 4 out (2 duplicates removed)
  name: text, 0 cells changed
  phone: phone, 3 cells changed
  email: email, 1 cells changed
  date: date, 4 cells changed
  amount: money, 6 cells changed
```

## Options

```
-o, --output FILE    .csv or .xlsx (default: stdout)
-d, --delimiter CH   input delimiter (default: auto)
--dayfirst           read 03/04/2026 as 3 April
--snake              snake_case headers
--report             print what changed
```

## Tests

```bash
python3 -m unittest test_tidycsv -v
```

## Don't want to do it yourself?

The same maintainer offers fixed-price, done-for-you data work:

- **PDF to Excel/CSV extraction** ($19, fixed price, paid through Gumroad checkout): [details and order](https://nolanjoyce.gumroad.com/l/wfllt?utm_source=github&utm_medium=social&utm_campaign=tidycsv)
- **Custom spreadsheet cleanup or automation script** ($49, fixed price, paid through Gumroad checkout): [details and order](https://nolanjoyce.gumroad.com/l/asaieh?utm_source=github&utm_medium=social&utm_campaign=tidycsv)

## License

MIT
