# GlobeVAC Dashboard 7.3

Streamlit dashboard for biological product storage and formulation research.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Navigation

The eight original tabs remain: Database overview, Storage & formulation, Products, Suppliers & formulation, Research priorities, Compare products, Key takeaways, and Data quality.

Version 7.3 adds three tabs:
- **Market Opportunities:** coverage-gap charts and heuristic research-priority queue; not market demand estimates.
- **Formulation Explorer:** buffer/pH distributions, storage-class heatmap, searchable excipient descriptions, CSV export.
- **Evidence Confidence:** transparent documentation completeness score (0–100), rubric, review queue and CSV export. The score does not verify correctness of a source.

The original source CSV is included unchanged. All three new tabs use the existing data. Global filters apply to the Formulation Explorer; the other new tabs operate on the full imported registry.

Website: https://www.globe-vac.com/

### Navigation (updated)
Use the left sidebar **Workspace** selector to switch among Explore, Formulation & suppliers, Research & insights, and Evidence & quality. Choose a page underneath. The sidebar's collapsible **Research filters** apply to research views; Database overview retains its independent filters. All eleven original pages remain available.

Navigation accessibility update: transparent GlobeVAC logo blends into the sidebar; high-contrast sidebar navigation with clear active state. Logo remains a Home/Reset button.
