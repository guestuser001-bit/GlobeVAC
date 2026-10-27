# GlobeVAC Biological Product Intelligence

## Start
1. Extract the ZIP.
2. Open a terminal in the `globevac-dashboard` folder.
3. `python -m pip install -r requirements.txt`
4. `python -m streamlit run app.py`

## Tabs
- Overview: temperature, buffer, pH, supplier charts.
- Product catalog: shortlisted identifiable product records and CSV export.
- Suppliers & formulation: supplier summary, buffer-temperature matrix, formulation evidence.
- Key takeaways: filter-aware observations and opportunity screening queue.
- Data quality: excluded entries, completeness, review export.

## Interpretation
All counts are computed from the bundled 195-row extracted CSV. The product shortlist is based on name heuristics and populated storage/formulation fields, not independent verification. Temperatures are classified for charting only; inspect the original text and source before use.
\n## Visual update\nThe Overview includes the GlobeVAC About Us and Our Services panels, styled to match the supplied reference. All data charts and existing analysis tabs remain operational.\n