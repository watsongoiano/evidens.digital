# PREVENT Guideline Data

This directory hosts PREVENT model coefficient CSV files and the analysis script.

- Place CSVs here, named by table/source, e.g., `prevent_coefficients_age.csv`.
- The script `analyze_prevent_excel.py` is the entrypoint to list/process files.

Quick run

```
python -m src.static.guidelines.prevent.analyze_prevent_excel
```

Integration notes
- Do not commit raw proprietary spreadsheets if they contain restricted data.
- Prefer normalized CSVs or a derived JSON that the app consumes.
- Keep file names stable to avoid breaking references.
