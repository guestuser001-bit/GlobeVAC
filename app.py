
import re
import base64
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import os

ROOT = Path(__file__).resolve().parent
# Derive the displayed version from the containing folder name.
_version_match = re.search(r"(?:^|-)v(\d+(?:[-.]\d+)*)$", ROOT.name, re.IGNORECASE)
APP_VERSION = f"v{_version_match.group(1)}" if _version_match else "version unknown"

st.set_page_config(page_title="GlobeVAC | Advancing Vaccine Thermostability", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")
GREEN = "#126B3B"
PALETTE = ["#0E5533","#3F9B57","#7DCB76","#A7DCA8","#59B9D4","#D5E5D8","#E5B961"]
st.markdown("""
<style>
.stApp {background:#F8FAF9;color:#14251D}
[data-testid="stSidebar"] {background:#101D17!important}
[data-testid="stSidebar"] {color:#F4FFF7!important}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {background:transparent}
[data-testid="stSidebar"] hr {border-color:#23352C}
[data-testid="stSidebar"] [data-testid="stImage"] img {border-radius:10px}
[data-testid="stSidebar"] a {color:#89E79B!important}
[data-testid="stSidebar"] [data-testid="stImage"] {padding:8px 0 12px}
.block-container {padding-top:1.35rem;max-width:1480px}
h1 {font-size:2.5rem!important;letter-spacing:-.045em}
h2,h3 {color:#153F2C!important}
[data-testid="stMetric"] {background:white;border:1px solid #E3EAE5;border-radius:14px;padding:18px}
[data-testid="stMetricLabel"] {font-size:14px}
div[data-testid="stPlotlyChart"] {background:#fff;border:1px solid #E3EAE5;border-radius:14px;padding:12px}
[data-testid="stSidebar"] [role="radiogroup"] {gap:4px}
[data-testid="stSidebar"] [role="radiogroup"] label {padding:8px 10px;border-radius:8px}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {background:#17492E}
.stButton>button[kind="primary"], .stDownloadButton>button {background:#125F38;color:white;border-radius:9px}
.gv-hero {padding:32px 30px;border-radius:16px;background:linear-gradient(105deg,#fff 0%,#fff 60%,#E8F4EC 100%);border:1px solid #E1EAE4;margin-bottom:18px}
.gv-hero h1 {margin:5px 0;color:#102A1E}
.gv-hero .green {color:#116D37}
.gv-eyebrow {font-size:11px;letter-spacing:3px;font-weight:750;color:#286147}
.gv-hero p {font-size:15px;color:#50635A;max-width:780px}
.gv-foot {color:#687A70;font-size:12px}
.gv-section {background:white;border:1px solid #E5EBE7;border-radius:15px;padding:25px 27px;height:100%;margin-top:6px}
.gv-section h2 {font-size:25px!important;letter-spacing:-.025em;margin:8px 0 10px;color:#152A1E!important}
.gv-section p {color:#56685E;line-height:1.6;font-size:14px}
.gv-item {display:flex;gap:15px;align-items:flex-start;margin-top:22px}
.gv-icon {background:#E7F5EA;color:#13703D;border-radius:50%;height:43px;min-width:43px;display:flex;align-items:center;justify-content:center;font-size:20px}
.gv-item b {font-size:14px;color:#1B3325}
.gv-item p {margin:3px 0 0;font-size:12px}
.gv-service-grid {display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px}
.gv-service {border:1px solid #E7EDE8;border-radius:11px;padding:13px;display:flex;gap:10px}
.gv-service .gv-icon {height:35px;min-width:35px;font-size:17px}
.gv-service b {font-size:12px}
.gv-service p {font-size:11px;line-height:1.45}
@media(max-width:1100px){.gv-service-grid {grid-template-columns:1fr}}

</style>
""",unsafe_allow_html=True)

@st.cache_data
def read_data():
    d=pd.read_csv(ROOT/"protein_storage_all_results.csv",dtype=str,keep_default_na=False).fillna("")
    for c in d.columns:d[c]=d[c].astype(str).str.strip()
    return d.drop_duplicates(subset=["product","manufacturer","storage_temperature","storage_buffer","storage_buffer_pH"]).copy()

EMPTY={"","unknown","n/a","na","none","not reported","not specified","-","—","null"}
def has_value(v):
    return str(v).strip().lower() not in EMPTY

def is_product(name):
    n=str(name).strip()
    if len(n)<8:return False
    if re.search(r"(?i)(protocols? book|technical faq|safe preparation|WHO/BS/|conjugation kit|guidelines?|handbook|datasheet|^faq$|storage for chemicals|^technical|^support)",n):return False
    return bool(re.search(r"(?i)(antibod|\bmab\b|monoclonal|polyclonal|recombinant.*protein|antigen\b)",n))

def buffer_system(v):
    v=str(v)
    for pattern,label in [(r"\bPBS\b","PBS"),(r"\bTBS\b","TBS"),(r"tris[\s-]?hcl","Tris-HCl"),(r"\bHEPES\b","HEPES"),(r"citrate","Citrate"),(r"histidine","Histidine")]:
        if re.search(pattern,v,re.I):return label
    return "Other / unspecified" if has_value(v) else "Not reported"

def temp_class(v):
    v=str(v).replace("−", "-").replace("–", "-")
    # Check ultra-low temperatures first so -70/-80°C are not classified as frozen.
    if re.search(r"(?<!\d)-\s*(?:50|60|70|80|90)\s*°?\s*C",v,re.I):
        return "Ultra-low temperature"
    if re.search(r"(?<!\d)-\s*(?:20|25|30|40)\s*°?\s*C",v,re.I):
        return "Frozen (≤ −20°C)"
    if re.search(r"(?:\b[234568]\s*°\s*C|2\s*(?:-|to)\s*8\s*°?\s*C)",v,re.I):
        return "Refrigerated (2–8°C)"
    if re.search(r"(?:ambient|room temperature|\b(?:20|22|25)\s*°?\s*C)",v,re.I):
        return "Ambient"
    return "Other / unclear"

def ph_number(v):
    vals=re.findall(r"(?<!\d)(?:[4-9](?:\.\d+)?|10(?:\.\d+)?)(?!\d)",str(v))
    return float(vals[0]) if vals else None

df=read_data()
for c in ["product","manufacturer","storage_temperature","storage_buffer","storage_buffer_pH"]:
    if c not in df:st.error("Missing column: "+c);st.stop()
df["buffer_system"]=df["storage_buffer"].map(buffer_system)
df["temperature_group"]=df["storage_temperature"].map(temp_class)
df["pH_numeric"]=df["storage_buffer_pH"].map(ph_number)
qual=df["storage_temperature"].map(has_value)&(df["storage_buffer"].map(has_value)|df["storage_buffer_pH"].map(has_value))
products=df[qual & df["product"].map(is_product)].copy()
review=df[qual & ~df["product"].map(is_product)].copy()

NAV_GROUPS = {
    "Explore products": ["Database overview", "Products", "Compare products"],
    "Formulations & suppliers": ["Storage & formulation", "Suppliers & formulation", "Formulation Explorer"],
    "Research & strategy": ["Market Opportunities", "Research priorities", "Key takeaways"],
    "Evidence & quality": ["Evidence Confidence", "Data quality"],
}
PAGE_ICONS = {"Home":"🏠", "Database overview":"🗂️", "Products":"📦", "Compare products":"⚖️", "Storage & formulation":"🧪", "Suppliers & formulation":"🏭", "Formulation Explorer":"🔬", "Market Opportunities":"🎯", "Research priorities":"📋", "Key takeaways":"💡", "Evidence Confidence":"🛡️", "Data quality":"📊"}
if "active_page" not in st.session_state:
    st.session_state.active_page="Home"
def navigate(destination):
    st.session_state.active_page=destination
    if destination=="Home":
        # Reset global and overview filters so Home is always a fresh starting point.
        for key in list(st.session_state):
            if key.startswith("overview_") or key in ("research_suppliers", "research_buffers", "research_temps", "research_ph_only", "research_query"):
                del st.session_state[key]

# The logo image is transparent; render it as a visible foreground image rather than
# relying on a CSS background image that Streamlit may override.
logo_b64=base64.b64encode((ROOT/"globevac-logo-transparent.png").read_bytes()).decode("ascii")
st.markdown(f"""<style>
/* Sidebar background and resting navigation controls share the same exact color. */
[data-testid="stSidebar"], [data-testid="stSidebarContent"] {{background:#101D17!important;}}
[data-testid="stSidebar"] .st-key-logo_home button {{
  background-color:#101D17!important;
  background-image:url('data:image/png;base64,{logo_b64}')!important;
  background-position:center!important;
  background-size:contain!important;
  background-repeat:no-repeat!important;
  min-height:100px!important;
  width:100%!important;
  border:0!important;
  box-shadow:none!important;
  color:transparent!important;
  outline-offset:2px;
}}
[data-testid="stSidebar"] .st-key-logo_home button p {{opacity:0!important;}}
[data-testid="stSidebar"] .st-key-logo_home button:hover,
[data-testid="stSidebar"] .st-key-logo_home button:focus,
[data-testid="stSidebar"] .st-key-logo_home button:active {{
  background-color:#101D17!important;
  border:0!important;
  box-shadow:none!important;
}}
/* Workspace expanders: blend with sidebar, maintain legible titles and opened content. */
[data-testid="stSidebar"] [data-testid="stExpander"],
[data-testid="stSidebar"] [data-testid="stExpander"] > details,
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpanderDetails"] {{background:#101D17!important;border-color:#2C4637!important;}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{background:#203B2C!important;}}
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] summary p,
[data-testid="stSidebar"] [data-testid="stExpander"] summary svg {{color:#F4FFF7!important;fill:currentColor;}}
[data-testid="stSidebar"] .stButton button:not(.st-key-logo_home button) {{
  width:100%;justify-content:flex-start!important;text-align:left!important;
  color:#F4FFF7!important;font-weight:600!important;box-shadow:none!important;
  border:1px solid transparent!important;border-radius:7px!important;
}}
[data-testid="stSidebar"] .stButton button[kind="secondary"] {{background:#101D17!important;}}
[data-testid="stSidebar"] .stButton button[kind="primary"] {{background:#24543A!important;border-left:3px solid #9CE4B4!important;color:#FFFFFF!important;}}
[data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {{background:#2C503A!important;}}
[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {{background:#306B4A!important;}}
[data-testid="stSidebar"] .stButton button p,
[data-testid="stSidebar"] .stButton button span {{color:inherit!important;opacity:1!important;}}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] label p {{color:#EDF8F0!important;}}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{color:#C3D7C9!important;}}
/* Homepage shortcut cards: equal height and bottom-aligned action buttons. */
.st-key-home_explore [data-testid="stHorizontalBlock"] {{align-items:stretch;}}
.st-key-home_explore [data-testid="column"] {{display:flex;flex-direction:column;}}
.st-key-home_explore [data-testid="column"] > [data-testid="stVerticalBlock"] {{flex:1;}}
.st-key-home_explore [data-testid="stVerticalBlockBorderWrapper"] {{height:100%;}}
.st-key-home_explore [data-testid="stVerticalBlockBorderWrapper"] > div {{height:100%;}}
.st-key-home_explore [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {{height:100%;display:flex;flex-direction:column;}}
.st-key-home_explore [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stButton"] {{margin-top:auto;}}
/* Logo home control: actual transparent GlobeVAC artwork, always visible. */
[data-testid="stSidebar"] div.st-key-logo_home button,
[data-testid="stSidebar"] div.st-key-logo_home button[kind="primary"] {{
  background-color:#101D17!important;
  background-image:url("data:image/png;base64,{logo_b64}")!important;
  background-position:center!important;
  background-size:92% auto!important;
  background-repeat:no-repeat!important;
  min-height:88px!important;
  border:1px solid transparent!important;
  border-radius:8px!important;
  box-shadow:none!important;
  color:transparent!important;
}}
[data-testid="stSidebar"] div.st-key-logo_home button:hover,
[data-testid="stSidebar"] div.st-key-logo_home button:focus-visible,
[data-testid="stSidebar"] div.st-key-logo_home button:active {{
  background-color:#267449!important;
  border-color:#6DB68A!important;
}}
[data-testid="stSidebar"] div.st-key-logo_home button p,
[data-testid="stSidebar"] div.st-key-logo_home button span {{visibility:hidden!important;}}
</style>""",unsafe_allow_html=True)
with st.sidebar:
    # Streamlit buttons are used instead of an image alone so the logo works as a home link.
    if st.button("🌍  GlobeVAC", key="logo_home", use_container_width=True, type="primary"):
        navigate("Home")
        st.rerun()
    st.caption(f"Advancing Vaccine Thermostability · zj · {APP_VERSION}")
    st.divider()
    st.caption("WORKSPACES")
    for group, pages in NAV_GROUPS.items():
        with st.expander(group, expanded=st.session_state.active_page in pages):
            for destination in pages:
                if st.button(f"{PAGE_ICONS[destination]}  {destination}", key="nav_"+destination,
                             use_container_width=True,
                             type="primary" if st.session_state.active_page==destination else "secondary"):
                    navigate(destination)
                    st.rerun()
    st.divider()
    st.caption("Select a page to explore. Click the GlobeVAC logo to return home.")
page=st.session_state.active_page
# Research filters are contextual, rather than competing with the database search.
# Keep the main controls compact; less frequently used options live under Advanced.
selected_suppliers=None
selected_buffers=None
selected_temp=None
ph_only=False
query=""
if page not in ("Home", "Database overview"):
    with st.sidebar:
        st.divider()
        st.markdown("**🔎 Search & filter**")
        query=st.text_input(
            "Find a product or protein", placeholder="Type a name to search…",
            key="research_query", help="Searches product and protein names."
        )
        suppliers=sorted(x for x in products.manufacturer.dropna().unique() if x)
        buffers=sorted(x for x in products.buffer_system.dropna().unique() if x)
        temp_groups=sorted(x for x in products.temperature_group.dropna().unique() if x)
        active_count=(bool(query.strip()) + bool(st.session_state.get("research_suppliers"))
                      + bool(st.session_state.get("research_buffers"))
                      + bool(st.session_state.get("research_temps"))
                      + bool(st.session_state.get("research_ph_only",False)))
        with st.expander(f"⚙️ Refine results" + (f" · {active_count} active" if active_count else ""), expanded=False):
            selected_suppliers=st.multiselect(
                "Supplier", suppliers, placeholder="Any supplier", key="research_suppliers"
            )
            selected_buffers=st.multiselect(
                "Buffer system", buffers, placeholder="Any buffer", key="research_buffers"
            )
            selected_temp=st.multiselect(
                "Storage temperature", temp_groups, placeholder="Any temperature", key="research_temps"
            )
            ph_only=st.checkbox("Only show records with pH data",key="research_ph_only")
        if active_count:
            if st.button("↺ Reset all filters",use_container_width=True,key="clear_research_filters"):
                for k in ("research_query","research_suppliers","research_buffers","research_temps","research_ph_only"):
                    st.session_state.pop(k,None)
                st.rerun()
        else:
            st.caption("Showing all research records · add filters to narrow results")

view=products.copy()
if selected_suppliers:view=view[view.manufacturer.isin(selected_suppliers)]
if selected_buffers:view=view[view.buffer_system.isin(selected_buffers)]
if selected_temp:view=view[view.temperature_group.isin(selected_temp)]
if ph_only:view=view[view.storage_buffer_pH.map(has_value)]
if query:
    q=re.escape(query)
    view=view[view["product"].str.contains(q,case=False,na=False)|view["protein"].str.contains(q,case=False,na=False)]
if page not in ("Home", "Database overview"):
    with st.sidebar:
        st.caption(f"**{len(view):,}** of **{len(products):,}** products match")
        if view.empty:
            st.info("No matches. Try a shorter search or reset the filters.")


def chart_layout(fig):
    fig.update_layout(
        margin=dict(l=20,r=24,t=55,b=25),height=335,
        paper_bgcolor="white",plot_bgcolor="white",
        font=dict(family="Arial",color="#294B3B",size=12),
        title_font=dict(size=16,color="#173F2B"),
        legend=dict(orientation="h",y=-.18),
        xaxis=dict(showgrid=False),yaxis=dict(gridcolor="#EDF2EE")
    )
    return fig

def export_csv(frame, name, label="Export CSV"):
    st.download_button(label, frame.to_csv(index=False).encode("utf-8-sig"),
                       file_name=name,mime="text/csv",key=name)

def show_table(frame, cols, height=350):
    show=frame.reindex(columns=cols).copy()
    show=show.fillna("").replace(r"^\\s*$","—",regex=True)
    config={"Source":st.column_config.LinkColumn("Source",display_text="View source")}
    st.dataframe(show,hide_index=True,use_container_width=True,height=height,
                 column_config=config)
    return show

def ph_bucket(v):
    n=ph_number(v)
    if n is None:return "Not reported"
    if n<6:return "< 6.0"
    if n<7:return "6.0–6.9"
    if n<8:return "7.0–7.9"
    if n<9:return "8.0–8.9"
    return "≥ 9.0"

def stability_signal(row):
    t=row.get("temperature_group","")
    if t=="Frozen (≤ −20°C)":return "Frozen storage reported"
    if t=="Refrigerated (2–8°C)":return "Refrigerated storage reported"
    return "Temperature requires review"

def formulation_signal(row):
    v=str(row.get("storage_buffer","")).lower()
    if re.search(r"glycerol|sucrose|trehalose|bsa|albumin|histidine",v):
        return "Formulation excipient mentioned"
    if has_value(row.get("storage_buffer_pH","")):
        return "pH information reported"
    if has_value(row.get("storage_buffer","")):
        return "Buffer information reported"
    return "Formulation detail limited"

view["pH group"]=view["storage_buffer_pH"].map(ph_bucket)
view["Storage signal"]=view.apply(stability_signal,axis=1)
view["Formulation signal"]=view.apply(formulation_signal,axis=1)

if page != "Home":
    st.markdown(f"<div class='gv-eyebrow'>GlobeVAC / {page.upper()}</div>", unsafe_allow_html=True)
    st.title(page)
    st.caption("Advancing Vaccine Thermostability · Source-based research data")

if page == 'Storage & formulation':
    st.subheader("Portfolio at a glance")
    k=st.columns(5)
    metrics=[
        ("Products in view",len(view)),
        ("Suppliers",view.manufacturer.replace("",pd.NA).nunique()),
        ("Frozen storage",int((view.temperature_group=="Frozen (≤ −20°C)").sum())),
        ("Buffer reported",int(view.storage_buffer.map(has_value).sum())),
        ("pH reported",int(view.storage_buffer_pH.map(has_value).sum()))
    ]
    for col,(label,val) in zip(k,metrics):col.metric(label,int(val))
    st.caption("A clear view of the currently filtered research dataset. All figures are extracted-data indicators, not verified manufacturer claims.")
    if len(view):
        completeness = round(100 * view.storage_buffer_pH.map(has_value).mean())
        st.progress(completeness/100, text=f"pH field coverage in current selection · {completeness}%")
    left,right=st.columns(2)
    with left:
        counts=view.temperature_group.value_counts()
        counts=counts.reindex(["Refrigerated (2–8°C)","Frozen (≤ −20°C)","Ultra-low temperature","Ambient"],fill_value=0)
        counts=counts[counts>0]
        fig=go.Figure(go.Pie(labels=counts.index,values=counts.values,hole=.64,
                             marker_colors=PALETTE,textinfo="percent"))
        fig.update_layout(title="Storage temperature distribution")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    with right:
        counts=view.buffer_system.value_counts().sort_values()
        fig=go.Figure(go.Bar(x=counts.values,y=counts.index,orientation="h",
                             marker_color="#3F9B57",text=counts.values,textposition="outside"))
        fig.update_layout(title="Buffer systems used",xaxis_title="Product records",yaxis_title="")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    left,right=st.columns(2)
    with left:
        order=["< 6.0","6.0–6.9","7.0–7.9","8.0–8.9","≥ 9.0"]
        counts=view["pH group"].value_counts().reindex(order,fill_value=0)
        fig=go.Figure(go.Bar(x=counts.index,y=counts.values,marker_color="#5EBB79",
                             text=counts.values,textposition="outside"))
        fig.update_layout(title="pH distribution",yaxis_title="Product records")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    with right:
        counts=view.manufacturer.replace("","Unknown").value_counts()
        fig=go.Figure(go.Pie(labels=counts.index,values=counts.values,hole=.62,
                             marker_colors=PALETTE,textinfo="percent"))
        fig.update_layout(title="Suppliers / manufacturers")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    st.caption("Frozen and refrigerated categories are simplified. A record with both frozen and refrigerated temperatures is counted as frozen; see the full temperature text in Product catalog.")




# Database overview: use the entire extracted dataset, not only formulation-complete records.
# Stable IDs are deterministic within the current normalized input. Manufacturer/catalog identity
# should be reconciled across source systems before treating IDs as persistent database keys.
import hashlib

def product_category(name):
    n=str(name).lower()
    if "vaccine" in n:return "Vaccine"
    if "antibod" in n or "monoclonal" in n or "polyclonal" in n or re.search(r"\bmab\b",n):return "Antibody"
    if "recombinant" in n and "protein" in n:return "Recombinant protein"
    if "antigen" in n:return "Antigen"
    if "protein" in n:return "Protein / other"
    return "Other / review"

def storage_class(v):
    """Conservative text classification; multi-temperature instructions are review-needed."""
    raw=str(v).strip()
    if not has_value(raw):return "Uncertain / review needed"
    t=raw.lower().replace("−","-").replace("–","-").replace("º","°")
    if re.search(r"(?:-80|-70|-60|-50)\s*°?\s*c",t):
        if re.search(r"(?:-20|-30|2\s*-\s*8|\b4\s*°?\s*c|\broom temperature\b)",t):
            return "Uncertain / review needed"
        return "Ultra-low temperature"
    if re.search(r"(?:-20|-25|-30|-40)\s*°?\s*c",t):
        if re.search(r"(?:2\s*-\s*8|\b4\s*°?\s*c|\broom temperature\b)",t):
            return "Uncertain / review needed"
        return "Frozen"
    if re.search(r"(?:2\s*-\s*8|2\s*to\s*8|\b4\s*°?\s*c|\b5\s*°?\s*c)",t):
        if "room temperature" in t:return "Uncertain / review needed"
        return "Refrigerated"
    if re.search(r"(?:room temperature|ambient|20\s*-\s*25\s*°?\s*c)",t):
        return "Ambient"
    if re.search(r"(?:°\s*c|degrees celsius)",t):
        return "Other controlled temperature"
    return "Uncertain / review needed"

def stable_key(row):
    import unicodedata
    # A provisional deterministic identifier; not a verified catalog ID.
    fields=[str(row.get(k,"")).strip().casefold() for k in ("manufacturer","product","uniprot_id")]
    key="|".join(fields)
    return "GV-"+hashlib.sha1(key.encode("utf-8")).hexdigest()[:10].upper()

database=df.copy()
database["Product ID"]=database.apply(stable_key,axis=1)
database["Product category"]=database["product"].map(product_category)
database["Storage classification"]=database["storage_temperature"].map(storage_class)
database["Record status"]=database["product"].map(lambda v:"Product-like (unverified)" if is_product(v) else "Review / non-product")
database["Source available"]=database["source"].map(has_value)
database["Temperature available"]=database["storage_temperature"].map(has_value)
database["Formulation available"]=database["storage_buffer"].map(has_value)|database["storage_buffer_pH"].map(has_value)
# The source CSV does not contain reliable shipping-temperature, geographic market,
# demand or catalog-number columns. Do not infer those values.
database["Shipping temperature"]="Not collected"
database["Market / country"]="Not collected"
database["Catalog number"]="Not collected"
database["Evidence status"]="Source linked · unverified"
database.loc[~database["Source available"],"Evidence status"]="Source missing · review"

# Transparent, heuristic evidence scoring: not independent source verification.
def evidence_score(row):
    score=0
    if has_value(row.get("source", "")): score+=25
    if has_value(row.get("storage_evidence", "")): score+=20
    if has_value(row.get("source_type", "")): score+=10
    if has_value(row.get("storage_temperature", "")): score+=15
    if has_value(row.get("storage_buffer", "")): score+=10
    if has_value(row.get("storage_buffer_pH", "")): score+=5
    if has_value(row.get("manufacturer", "")): score+=10
    if is_product(row.get("product", "")): score+=5
    return score

def evidence_band(score):
    if score>=80:return "High documentation coverage"
    if score>=55:return "Moderate documentation coverage"
    return "Low documentation coverage"

database["Evidence score"]=database.apply(evidence_score,axis=1)
database["Evidence confidence"]=database["Evidence score"].map(evidence_band)
# Scores reflect populated fields, NOT factual validation or manufacturer endorsement.

if page == "Home":
    st.markdown("""<div class="gv-hero"><div class="gv-eyebrow">GlobeVAC · VACCINE THERMOSTABILITY</div>
    <h1>Advancing <span class="green">Vaccine Thermostability</span></h1>
    <p>Pioneering biologics stability solutions that ensure vaccines reach every corner of the globe — safely and effectively. Explore the evidence, products and formulation insights supporting this mission.</p></div>""", unsafe_allow_html=True)
    n=len(database)
    source_count=int(database["Source available"].sum())
    temp_count=int(database["Temperature available"].sum())
    low_count=int((database["Evidence score"]<55).sum())
    suppliers_count=database.loc[database.manufacturer.map(has_value),"manufacturer"].nunique()
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Imported records",f"{n:,}",help="Deduplicated rows; not necessarily distinct commercial products")
    m2.metric("Suppliers represented",f"{suppliers_count:,}")
    m3.metric("Storage information",f"{temp_count/n:.0%}" if n else "0%")
    m4.metric("Source coverage",f"{source_count/n:.0%}" if n else "0%")
    st.caption("Metrics are calculated from the imported research dataset; product identity and scientific claims have not been independently verified.")
    st.markdown("### Start exploring")
    st.caption("Choose where to begin. Each shortcut opens its corresponding research page.")
    with st.container(key="home_explore"):
        c1,c2,c3=st.columns(3, gap="medium")
        with c1:
            with st.container(border=True):
                st.markdown("**🗂️ Find a product**")
                st.write("Search the database, inspect product records and open original sources.")
                if st.button("Open database →",use_container_width=True,key="home_db"):
                    navigate("Database overview");st.rerun()
        with c2:
            with st.container(border=True):
                st.markdown("**🔬 Explore formulations**")
                st.write("Explore buffer systems, pH values and storage-temperature patterns.")
                if st.button("Explore formulations →",use_container_width=True,key="home_form"):
                    navigate("Formulation Explorer");st.rerun()
        with c3:
            with st.container(border=True):
                st.markdown("**🎯 Find opportunities**")
                st.write("Discover potential research gaps and prioritize hypotheses to investigate.")
                if st.button("View opportunities →",use_container_width=True,key="home_market"):
                    navigate("Market Opportunities");st.rerun()
    st.markdown("### Key signals from the database")
    left,right=st.columns([1.2,1])
    with left:
        st.markdown("**Storage conditions reported**")
        counts=database["Storage classification"].value_counts().head(7)
        if len(counts):
            fig=go.Figure(go.Bar(x=counts.values,y=counts.index,orientation="h",marker_color="#126B3B"))
            fig.update_layout(height=300,margin=dict(l=8,r=15,t=10,b=25),yaxis=dict(autorange="reversed"),paper_bgcolor="white",plot_bgcolor="white",xaxis_title="Records")
            st.plotly_chart(fig,use_container_width=True)
    with right:
        st.markdown("**Research attention needed**")
        st.metric("Low documentation coverage",f"{low_count:,}",help="Heuristic completeness score below 55; not a validation of scientific accuracy")
        st.metric("Storage needs review",f"{(database['Storage classification']=='Uncertain / review needed').sum():,}")
        st.write("These are opportunities to improve source documentation, not evidence of product instability.")
        if st.button("Review evidence quality →",use_container_width=True,key="home_evidence"):
            navigate("Evidence Confidence");st.rerun()
    st.markdown("### Discover GlobeVAC")
    st.markdown("#### Our mission and stability solutions")
    st.markdown("""
<div class="gv-section">
  <div class="gv-eyebrow">ABOUT US</div>
  <h2>Redefining Biologics Stability</h2>
  <p>GlobeVAC is dedicated to solving one of global health's most critical challenges: ensuring vaccines and biologics remain potent regardless of environmental conditions.</p>
  <div class="gv-item"><span class="gv-icon">◎</span><div><b>Our Mission</b><p>To make every vaccine thermostable, eliminating cold chain dependency and expanding global access to life-saving biologics.</p></div></div>
  <div class="gv-item"><span class="gv-icon">◉</span><div><b>Global Reach</b><p>Our solutions are designed for the most challenging environments — from tropical climates to remote communities with limited infrastructure.</p></div></div>
  <div class="gv-item"><span class="gv-icon">✧</span><div><b>Scientific Excellence</b><p>Backed by rigorous research and development, our proprietary formulations push the boundaries of what's possible in vaccine stability.</p></div></div>
</div>""",unsafe_allow_html=True)
    st.markdown("""
<div class="gv-section">
  <div class="gv-eyebrow">OUR SERVICES</div>
  <h2>End-to-End Stability Solutions</h2>
  <p>From early-stage formulation through regulatory approval, we provide comprehensive thermostability services for vaccines and biologics.</p>
  <div class="gv-service-grid">
    <div class="gv-service"><span class="gv-icon">♧</span><div><b>Thermostability Engineering</b><p>Advanced formulation technologies that extend vaccine shelf life at ambient temperatures, reducing cold chain requirements.</p></div></div>
    <div class="gv-service"><span class="gv-icon">▥</span><div><b>Stability Testing &amp; Analysis</b><p>Comprehensive accelerated and real-time stability studies compliant with ICH and WHO guidelines.</p></div></div>
    <div class="gv-service"><span class="gv-icon">↗</span><div><b>Cold Chain Optimization</b><p>Strategic solutions to minimize cold chain dependency while maintaining product integrity throughout distribution.</p></div></div>
    <div class="gv-service"><span class="gv-icon">⚙</span><div><b>Formulation Development</b><p>Custom biologics formulation services leveraging proprietary stabilizer technologies and excipient platforms.</p></div></div>
    <div class="gv-service"><span class="gv-icon">❄</span><div><b>Lyophilization Services</b><p>State-of-the-art freeze-drying processes optimized for maximum stability and reconstitution performance.</p></div></div>
    <div class="gv-service"><span class="gv-icon">▤</span><div><b>Regulatory Support</b><p>Expert guidance navigating global regulatory pathways for thermostable vaccine products and biologics.</p></div></div>
  </div>
</div>""",unsafe_allow_html=True)


if page == 'Database overview':
    st.subheader("Database overview")
    st.write("**Start here:** see what is in the database, narrow the records, and open the original source for any product.")
    st.caption("This page includes all imported records. Other research tabs may use a smaller formulation-qualified subset. All classifications are screening labels, not verified product claims.")

    # Give users a clear sequence: summary → find → inspect → explore.
    total=len(database)
    named=int(database["manufacturer"].map(has_value).sum())
    stored=int(database["Temperature available"].sum())
    linked=int(database["Source available"].sum())
    k1,k2,k3,k4=st.columns(4)
    k1.metric("Records",f"{total:,}",help="Rows in the deduplicated imported dataset; not necessarily unique commercial products")
    k2.metric("Suppliers",f"{database.loc[database.manufacturer.map(has_value),'manufacturer'].nunique():,}")
    k3.metric("Storage documented",f"{stored/total:.0%}" if total else "0%",help=f"{stored:,} records with storage text")
    k4.metric("Source linked",f"{linked/total:.0%}" if total else "0%",help=f"{linked:,} records with a source URL")

    st.markdown("#### 1 · Find records")
    st.caption("Search here to filter the database. Research pages have their own contextual filters in the sidebar.")
    lookup=st.text_input("Search product, supplier, protein or product ID",placeholder="Search the database…",key="overview_search")
    categories=sorted(database["Product category"].unique().tolist())
    storage_options=sorted(database["Storage classification"].unique().tolist())
    evidence_options=["All records","Has source link","Missing source link","Needs storage review","Low documentation coverage"]
    selected_categories=[]
    selected_storage=[]
    evidence_filter="All records"
    with st.expander("Refine results · optional filters",expanded=False):
        f1,f2,f3=st.columns(3)
        selected_categories=f1.multiselect("Product category",categories,placeholder="All categories",key="overview_categories")
        selected_storage=f2.multiselect("Storage classification",storage_options,placeholder="All storage types",key="overview_storage")
        evidence_filter=f3.selectbox("Evidence / review",evidence_options,key="overview_evidence_filter")
        if st.button("Clear database filters",key="clear_overview_filters"):
            for k in ("overview_search","overview_categories","overview_storage","overview_evidence_filter"):
                st.session_state.pop(k,None)
            st.rerun()
    reg=database.copy()
    if lookup:
        needle=re.escape(lookup.strip())
        mask=pd.Series(False,index=reg.index)
        for col in ["product","manufacturer","protein","Product ID"]:
            if col in reg:mask=mask|reg[col].astype(str).str.contains(needle,case=False,na=False)
        reg=reg[mask]
    if selected_categories:reg=reg[reg["Product category"].isin(selected_categories)]
    if selected_storage:reg=reg[reg["Storage classification"].isin(selected_storage)]
    if evidence_filter=="Has source link":reg=reg[reg["Source available"]]
    elif evidence_filter=="Missing source link":reg=reg[~reg["Source available"]]
    elif evidence_filter=="Needs storage review":reg=reg[reg["Storage classification"]=="Uncertain / review needed"]
    elif evidence_filter=="Low documentation coverage":reg=reg[reg["Evidence score"]<55]
    st.markdown(f"**{len(reg):,} matching records** out of {total:,}")
    if reg.empty:
        st.info("No matching records. Clear the search or choose fewer filters to broaden your results.")
    else:
        st.markdown("#### 2 · Browse results")
        st.caption("Select a row to inspect its storage, formulation and evidence details. Open source links to verify claims.")
        registry=reg.rename(columns={"product":"Product","manufacturer":"Supplier","storage_temperature":"Storage text","source":"Source URL"})
        columns=["Product","Supplier","Product category","Storage classification","Evidence score","Source URL","Product ID"]
        event=st.dataframe(registry[columns].fillna(""),hide_index=True,use_container_width=True,height=370,
            on_select="rerun",selection_mode="single-row",key="overview_registry",
            column_config={"Source URL":st.column_config.LinkColumn("Source",display_text="Open source"),"Evidence score":st.column_config.ProgressColumn("Documentation",min_value=0,max_value=100,format="%d")})
        selected=event.selection.rows
        if selected:
            item=reg.iloc[selected[0]]
            st.markdown("##### Selected record details")
            st.markdown(f"**{item['product'] or 'Unnamed product'}** · {item['manufacturer'] or 'Supplier not reported'}")
            d1,d2=st.columns(2)
            d1.write("**Storage instructions (extracted)**")
            d1.write(item.get("storage_temperature") or "Not reported")
            d1.write("**Buffer (extracted)**")
            d1.write(item.get("storage_buffer") or "Not reported")
            d2.write("**pH (extracted)**")
            d2.write(item.get("storage_buffer_pH") or "Not reported")
            d2.write("**Evidence score**")
            d2.write(f"{item['Evidence score']}/100 — {item['Evidence confidence']}")
            st.write("**Storage evidence (extracted)**")
            st.write(item.get("storage_evidence") or "No evidence excerpt available")
            if has_value(item.get("source","")):
                source_url=str(item["source"]).strip()
                if source_url.startswith(("https://","http://")):st.link_button("Open original source",source_url)
            st.caption("Documentation score reflects populated fields, not scientific verification. Product IDs are provisional.")
        export_csv(registry[columns],"GlobeVAC_overview_filtered.csv","Download matching records (CSV)")

    st.markdown("#### 3 · Understand the dataset")
    st.caption("Charts reflect the matching records above. 'Uncertain / review needed' includes missing or ambiguous storage text.")
    left,right=st.columns(2)
    with left:
        counts=reg["Storage classification"].value_counts().sort_values()
        fig=go.Figure(go.Bar(y=counts.index,x=counts.values,orientation="h",marker_color="#3F9B57",text=counts.values,textposition="outside"))
        fig.update_layout(title="Storage categories",xaxis_title="Records",yaxis_title="")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    with right:
        counts=reg["Product category"].value_counts().sort_values()
        fig=go.Figure(go.Bar(y=counts.index,x=counts.values,orientation="h",marker_color="#126B3B",text=counts.values,textposition="outside"))
        fig.update_layout(title="Product categories",xaxis_title="Records",yaxis_title="")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    with st.expander("Supplier coverage and data limitations"):
        supplier_stats=(reg.assign(Supplier=reg["manufacturer"].where(reg["manufacturer"].map(has_value),"Unknown"))
            .groupby("Supplier",as_index=False)
            .agg(Records=("Product ID","size"),Products=("Product ID","nunique"),Storage_reported=("Temperature available","sum"),Sources_linked=("Source available","sum"))
            .sort_values(["Products","Supplier"],ascending=[False,True]))
        st.dataframe(supplier_stats.rename(columns={"Storage_reported":"Storage stated","Sources_linked":"Sources linked"}),hide_index=True,use_container_width=True,height=240)
        st.info("Storage is not shipping temperature. Catalog numbers, shipping conditions, country availability and market demand are not reliably collected in this dataset. Product categories and IDs are derived from extracted text.")
    st.caption("Next: use **Storage & formulation** for storage patterns, **Products** for the qualified catalog, and **Evidence Confidence** for records needing verification.")

if page == 'Products':
    st.subheader(f"Product catalog · {len(view)} records")
    st.write("Only identifiable products with a temperature and either a buffer or pH field are shown. Missing details are marked with a dash rather than guessed.")
    t=view.rename(columns={
        "product":"Product","manufacturer":"Supplier",
        "storage_temperature":"Storage temperature",
        "buffer_system":"Buffer system",
        "storage_buffer_pH":"Extracted pH","source":"Source",
        "protein":"Associated protein"
    })
    cols=["Product","Supplier","Storage temperature","Buffer system","Extracted pH","Source"]
    show=show_table(t,cols,height=540)
    export_csv(show,"globevac_product_catalog.csv","⬇ Export product catalog")
    with st.expander("Product-level formulation and evidence details"):
        detail=t.rename(columns={"storage_buffer":"Full extracted buffer",
                                 "storage_notes":"Storage notes",
                                 "storage_evidence":"Storage evidence"})
        detail_cols=["Product","Supplier","Full extracted buffer","Extracted pH","Storage notes","Storage evidence"]
        show_table(detail,detail_cols,height=360)
    st.caption("Some extracted pH values may come from contextual text rather than the actual formulation. Verify product datasheets before using results for sales or R&D.")

if page == 'Suppliers & formulation':
    st.subheader("Supplier & formulation intelligence")
    st.write("Compare supplier coverage and formulation patterns without treating missing fields as confirmed formulation ingredients.")
    supplier_rows=[]
    for supplier,g in view.groupby("manufacturer",dropna=False):
        supplier_rows.append({
            "Supplier":supplier or "Unknown",
            "Products":len(g),
            "Frozen storage":int((g.temperature_group=="Frozen (≤ −20°C)").sum()),
            "Refrigerated storage":int((g.temperature_group=="Refrigerated (2–8°C)").sum()),
            "Buffer reported":int(g.storage_buffer.map(has_value).sum()),
            "pH reported":int(g.storage_buffer_pH.map(has_value).sum()),
        })
    suppliers_table=pd.DataFrame(supplier_rows)
    if not suppliers_table.empty:
        suppliers_table=suppliers_table.sort_values(["Products","Supplier"],ascending=[False,True])
    st.markdown("#### Supplier coverage")
    st.dataframe(suppliers_table,hide_index=True,use_container_width=True)
    export_csv(suppliers_table,"globevac_supplier_summary.csv","⬇ Export supplier summary")
    st.markdown("#### Buffer × storage temperature")
    cross=pd.crosstab(view.buffer_system,view.temperature_group)
    st.dataframe(cross,use_container_width=True)
    st.caption("Counts are based on the first recognized buffer system in each extracted text field. A formulation may contain multiple buffer-related ingredients.")
    st.markdown("#### Formulation evidence matrix")
    evidence=view[["product","manufacturer","storage_temperature","buffer_system","storage_buffer_pH","Formulation signal"]].copy()
    evidence.columns=["Product","Supplier","Storage temperature","Buffer system","Extracted pH","Formulation evidence"]
    show_table(evidence,list(evidence.columns),height=360)
    export_csv(evidence,"globevac_formulation_matrix.csv","⬇ Export formulation matrix")


if page == 'Research priorities':
    st.subheader("Research priorities")
    st.caption("A practical queue of records to verify next. These are evidence-based screening labels, not commercial opportunity scores.")
    if view.empty:
        st.info("No products match the current filters.")
    else:
        priority=view.copy()
        priority["Verification focus"] = priority.apply(
            lambda r: "Confirm frozen-storage requirements" if r["temperature_group"]=="Frozen (≤ −20°C)"
            else ("Confirm refrigerated-storage requirements" if r["temperature_group"]=="Refrigerated (2–8°C)"
                  else "Clarify temperature wording"),axis=1)
        priority["Formulation follow-up"] = priority.apply(
            lambda r: "Verify pH and buffer context" if has_value(r["storage_buffer_pH"])
            else "Request or locate formulation pH",axis=1)
        priority["Source available"] = priority["source"].map(lambda v:"Yes" if str(v).startswith(("http://","https://")) else "Check")
        st.markdown("#### Records to investigate")
        priority_table=priority[["product","manufacturer","storage_temperature","buffer_system","Verification focus","Formulation follow-up","Source available"]].copy()
        priority_table.columns=["Product","Supplier","Storage temperature","Buffer system","Storage follow-up","Formulation follow-up","Source link"]
        st.dataframe(priority_table,hide_index=True,use_container_width=True,height=420)
        export_csv(priority_table,"globevac_research_priorities.csv","⬇ Export research priorities")
        st.markdown("#### Research workflow")
        c1,c2,c3=st.columns(3)
        with c1:
            st.markdown("**01 · Validate**")
            st.caption("Check product identity, storage wording, and formulation values against original supplier datasheets.")
        with c2:
            st.markdown("**02 · Understand**")
            st.caption("Identify whether the temperature reflects shipping, long-term storage, or post-reconstitution conditions.")
        with c3:
            st.markdown("**03 · Prioritize**")
            st.caption("Select technically relevant formulations for stability discussions and further research.")

if page == 'Compare products':
    st.subheader("Compare products")
    st.caption("Choose up to three records to compare the reported formulation and storage fields side by side.")
    if view.empty:
        st.info("No products available for comparison under the current filters.")
    else:
        choices=view.reset_index(drop=True).copy()
        choices["display"] = choices["product"].astype(str)+" · "+choices["manufacturer"].astype(str)+" · #"+(choices.index+1).astype(str)
        selected=st.multiselect("Products to compare",choices["display"].tolist(),default=choices["display"].head(min(2,len(choices))).tolist(),max_selections=3)
        if selected:
            comp=choices[choices["display"].isin(selected)].copy()
            rows=[("Product","product"),( "Supplier","manufacturer"),("Associated protein","protein"),
                  ("Storage temperature","storage_temperature"),("Buffer classification","buffer_system"),
                  ("Extracted buffer text","storage_buffer"),("Extracted pH","storage_buffer_pH"),
                  ("Storage notes","storage_notes"),("Source","source")]
            comparison=pd.DataFrame({"Attribute":[a for a,_ in rows]})
            for _,record in comp.iterrows():
                comparison[record["display"]] = [str(record.get(col,"")).strip() or "—" for _,col in rows]
            st.dataframe(comparison,hide_index=True,use_container_width=True,height=390)
            export_csv(comparison,"globevac_product_comparison.csv","⬇ Export comparison")
        else:
            st.info("Select one or more products above.")
        st.caption("Side-by-side values are extracted source text; they may refer to different storage stages or contexts.")

if page == 'Key takeaways':
    st.subheader("Key takeaways")
    st.write("Automatically generated observations from the currently filtered data. These are research signals, not validated product claims.")
    total=len(view)
    frozen=int((view.temperature_group=="Frozen (≤ −20°C)").sum())
    refrigerated=int((view.temperature_group=="Refrigerated (2–8°C)").sum())
    ph_count=int(view.storage_buffer_pH.map(has_value).sum())
    buffer_count=int(view.storage_buffer.map(has_value).sum())
    if total==0:
        st.info("No products match the current filters. Adjust the filters above.")
    else:
        dominant=view.buffer_system.value_counts()
        top_buffer=dominant.index[0] if len(dominant) else "None"
        top_supplier=view.manufacturer.value_counts()
        leader=top_supplier.index[0] if len(top_supplier) else "None"
        st.markdown(f"""
**Storage and cold-chain screening.** {frozen} of {total} shortlisted products ({frozen/total:.0%}) mention frozen storage, while {refrigerated} ({refrigerated/total:.0%}) fall into the refrigerated category. These are storage-condition signals, not proof of logistics requirements.

**Formulation visibility.** {buffer_count} of {total} records ({buffer_count/total:.0%}) include buffer text; {ph_count} ({ph_count/total:.0%}) include a pH field. Missing pH is a research gap, not an indication that the product lacks a defined pH.

**Most common buffer classification.** {top_buffer} is the largest category among the filtered records. Buffer classifications are text-derived and may not represent full final formulations.

**Supplier concentration.** {leader} has the largest number of records in this filtered dataset. This reflects the coverage of the research CSV, not market share.
""")
        st.markdown("#### GlobeVAC opportunity-screening queue")
        queue=view[["product","manufacturer","storage_temperature","Storage signal","Formulation signal"]].copy()
        queue.columns=["Product","Supplier","Storage temperature","Storage signal","Formulation signal"]
        queue=queue.sort_values(["Storage signal","Supplier","Product"])
        st.dataframe(queue,hide_index=True,use_container_width=True,height=330)
        export_csv(queue,"globevac_opportunity_screening.csv","⬇ Export screening queue")
        st.markdown("#### Suggested next actions")
        st.markdown("""
1. **Validate** the storage temperature, buffer and pH against manufacturer datasheets.
2. **Prioritize** products with frozen storage for stability and cold-chain feasibility discussions.
3. **Investigate** records with disclosed excipients for formulation benchmarking.
4. **Contact suppliers only after verification** of product identity and supporting source evidence.
""")
        st.caption("No commercial opportunity score is assigned: the CSV does not establish supplier needs, sales potential, or validated instability.")

if page == 'Data quality':
    st.subheader("Data quality & review")
    a,b,c,d=st.columns(4)
    for col,label,val in zip([a,b,c,d],
        ["Unique source rows","Field-qualified","Identifiable shortlist","Needs identity review"],
        [len(df),int(qual.sum()),len(products),len(review)]):
        col.metric(label,int(val))
    st.warning("Product detection uses name-based heuristics. General documents and other questionable entries are separated, but shortlisted products still require source verification.")
    st.markdown("#### Records withheld from product catalog")
    cols=["product","manufacturer","storage_temperature","storage_buffer","storage_buffer_pH"]
    st.dataframe(review[cols],hide_index=True,use_container_width=True,height=300)
    export_csv(review,"globevac_needs_review.csv","⬇ Export review records")
    st.markdown("#### Research coverage")
    coverage=pd.DataFrame([
        {"Field":"Storage temperature","Records":int(df.storage_temperature.map(has_value).sum())},
        {"Field":"Buffer text","Records":int(df.storage_buffer.map(has_value).sum())},
        {"Field":"pH text","Records":int(df.storage_buffer_pH.map(has_value).sum())},
        {"Field":"Manufacturer","Records":int(df.manufacturer.map(has_value).sum())},
        {"Field":"Source link","Records":int(df.source.map(has_value).sum())}
    ])
    st.dataframe(coverage,hide_index=True,use_container_width=True)
if page == 'Market Opportunities':
    st.subheader("Market Opportunities · research hypotheses")
    st.caption("Coverage gaps are inferred only from this dataset. They are not demand forecasts, validated technical feasibility, or proof of commercial opportunity.")
    opportunity=database[database["Record status"]=="Product-like (unverified)"].copy()
    if opportunity.empty:
        st.info("No product-like records available under the current identification rules.")
    else:
        category=st.selectbox("Product category",["All"]+sorted(opportunity["Product category"].unique().tolist()),key="opp_category")
        if category!="All":opportunity=opportunity[opportunity["Product category"]==category]
        byclass=(opportunity.groupby("Storage classification",dropna=False)
            .agg(Records=("Product ID","size"),Suppliers=("manufacturer","nunique"),Mean_evidence_score=("Evidence score","mean"))
            .reset_index().sort_values("Records"))
        st.markdown("#### Storage-class coverage")
        fig=go.Figure(go.Bar(x=byclass["Storage classification"],y=byclass["Records"],marker_color="#23834E"))
        fig.update_layout(title="Observed records by storage class",xaxis_title="Storage class",yaxis_title="Records")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
        st.dataframe(byclass.round(1),hide_index=True,use_container_width=True)
        st.markdown("#### Candidate verification priorities")
        st.caption("Prioritizes sparse supplier coverage, incomplete documentation, and uncertain storage classifications; this is a research queue, not a product recommendation.")
        counts=opportunity.groupby(["Product category","Storage classification"],dropna=False).agg(Records=("Product ID","size"),Suppliers=("manufacturer","nunique"),Average_score=("Evidence score","mean")).reset_index()
        counts["Priority score"]=(40/(counts["Suppliers"].clip(lower=1))+40*(1-counts["Average_score"]/100)+20*counts["Storage classification"].eq("Uncertain / review needed")).round(1)
        counts=counts.sort_values("Priority score",ascending=False)
        st.dataframe(counts.round(1),hide_index=True,use_container_width=True)
        export_csv(counts,"GlobeVAC_market_opportunity_hypotheses.csv","Export research priorities")
        st.info("Next validation: confirm source documents, measure external demand, assess stability experiments and regulatory requirements before development decisions.")

if page == 'Formulation Explorer':
    st.subheader("Formulation Explorer")
    st.caption("Descriptive associations from extracted records; these charts do not establish stability, causation, or formulation performance.")
    f=view.copy()
    if f.empty:
        st.info("No records match the global dashboard filters. Adjust filters above.")
    else:
        left,right=st.columns(2)
        with left:
            n=f["buffer_system"].value_counts().head(12)
            fig=go.Figure(go.Bar(x=n.index,y=n.values,marker_color="#23834E"))
            fig.update_layout(title="Buffer system frequency",xaxis_title="Buffer system",yaxis_title="Records")
            st.plotly_chart(chart_layout(fig),use_container_width=True)
        with right:
            n=f["pH group"].value_counts()
            fig=go.Figure(go.Bar(x=n.index,y=n.values,marker_color="#59B9D4"))
            fig.update_layout(title="Reported pH distribution",xaxis_title="pH group",yaxis_title="Records")
            st.plotly_chart(chart_layout(fig),use_container_width=True)
        st.markdown("#### Buffer × storage category")
        cross=pd.crosstab(f["buffer_system"],f["temperature_group"])
        fig=go.Figure(go.Heatmap(z=cross.values,x=cross.columns.tolist(),y=cross.index.tolist(),colorscale="Greens",hovertemplate="Buffer: %{y}<br>Storage: %{x}<br>Records: %{z}<extra></extra>"))
        fig.update_layout(title="Observed formulation/storage combinations",height=max(350,30*len(cross)))
        st.plotly_chart(fig,use_container_width=True)
        term=st.text_input("Search excipients in buffer descriptions",placeholder="e.g. trehalose, glycerol",key="excipient_search")
        if term:
            f=f[f["storage_buffer"].str.contains(re.escape(term),case=False,na=False)]
        cols=["product","manufacturer","storage_buffer","storage_buffer_pH","storage_temperature","source"]
        st.dataframe(f.reindex(columns=cols),hide_index=True,use_container_width=True,height=320)
        export_csv(f[cols],"GlobeVAC_formulation_explorer.csv","Export formulation records")

if page == 'Evidence Confidence':
    st.subheader("Evidence Confidence · documentation coverage")
    st.caption("This transparent 0–100 score measures presence of fields only. It is NOT a source reliability rating, independent verification, or confidence that reported storage conditions are correct.")
    evidence=database.copy()
    levels=evidence["Evidence confidence"].value_counts()
    a,b,c=st.columns(3)
    a.metric("Mean documentation score",f"{evidence['Evidence score'].mean():.1f}/100")
    b.metric("High coverage",int(levels.get("High documentation coverage",0)))
    c.metric("Low coverage",int(levels.get("Low documentation coverage",0)))
    st.bar_chart(levels)
    with st.expander("Scoring rubric",expanded=True):
        st.markdown("Source link **25** · storage evidence text **20** · source type **10** · storage temperature **15** · buffer text **10** · pH **5** · manufacturer **10** · product-like name **5**. High ≥80, moderate 55–79, low <55. Missing fields score zero; populated fields are not automatically verified.")
    threshold=st.slider("Maximum score to review",0,100,55,5,key="evidence_threshold")
    evidence=evidence[evidence["Evidence score"]<=threshold].sort_values(["Evidence score","product"])
    st.write(f"{len(evidence):,} records meet the review threshold")
    cols=["Product ID","product","manufacturer","Evidence score","Evidence confidence","storage_temperature","source_type","source"]
    st.dataframe(evidence[cols],hide_index=True,use_container_width=True,height=360,column_config={"source":st.column_config.LinkColumn("Source",display_text="Open source")})
    export_csv(evidence[cols],"GlobeVAC_evidence_review.csv","Export evidence review queue")

st.markdown('<p class="gv-foot">GlobeVAC · Advancing Vaccine Thermostability · Extracted data requires manufacturer validation</p>',unsafe_allow_html=True)
