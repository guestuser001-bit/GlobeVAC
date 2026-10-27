
import re
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="GlobeVAC | Biological Product Intelligence", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")
GREEN = "#126B3B"
PALETTE = ["#0E5533","#3F9B57","#7DCB76","#A7DCA8","#59B9D4","#D5E5D8","#E5B961"]
st.markdown("""
<style>
.stApp {background:#F8FAF9;color:#14251D}
[data-testid="stSidebar"] {background:#010100!important}
[data-testid="stSidebar"] * {color:#F4FFF7!important}
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
[data-baseweb="tab-list"] {gap:19px}
[data-baseweb="tab"] {font-weight:700}
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
    v=str(v)
    if re.search(r"(?<!\d)[−-]\s*(?:20|25|30|40|50|60|70|80)\s*°?\s*C",v,re.I):return "Frozen (≤ −20°C)"
    if re.search(r"(?:\b[234568]\s*°\s*C|2\s*(?:-|–|to)\s*8\s*°?\s*C)",v,re.I):return "Refrigerated (2–8°C)"
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

with st.sidebar:
    st.image(str(ROOT/"globevac-logo.png"),use_container_width=True)
    st.caption("VACCINE THERMOSTABILITY")
    st.divider()
    st.markdown("**Explore**")
    st.markdown("**Overview**  ·  **Products**  ·  **Suppliers**")
    st.markdown("**Key takeaways**  ·  **About us**  ·  **Our services**")
    st.divider()
    st.image(str(ROOT/"vaccine-vial.png"),use_container_width=True)
    st.markdown("**Stable vaccines. A healthier world.**")
    st.caption("Pioneering vaccine thermostability and biologics stability solutions.")
    st.markdown("[GlobeVAC website](https://www.globe-vac.com/)")

st.markdown("""<div class="gv-hero"><div class="gv-eyebrow">VACCINE THERMOSTABILITY</div>
<h1>Advancing <span class="green">Vaccine Thermostability</span></h1>
<p>Pioneering biologics stability solutions that ensure vaccines reach every corner of the globe — safely and effectively.</p></div>""",unsafe_allow_html=True)

with st.expander("Filter dashboard",expanded=True):
    a,b,c,d=st.columns(4)
    suppliers=sorted(x for x in products.manufacturer.unique() if x)
    selected_suppliers=a.multiselect("Supplier",suppliers,default=suppliers)
    buffers=sorted(products.buffer_system.unique())
    selected_buffers=b.multiselect("Buffer system",buffers,default=buffers)
    temp_groups=sorted(products.temperature_group.unique())
    selected_temp=c.multiselect("Temperature category",temp_groups,default=temp_groups)
    ph_only=d.checkbox("Only records with pH",False)
    query=st.text_input("Search product names or proteins",placeholder="e.g. Adenovirus")
view=products[products.manufacturer.isin(selected_suppliers)&products.buffer_system.isin(selected_buffers)&products.temperature_group.isin(selected_temp)].copy()
if ph_only:view=view[view.storage_buffer_pH.map(has_value)]
if query:
    q=re.escape(query)
    view=view[view["product"].str.contains(q,case=False,na=False)|view["protein"].str.contains(q,case=False,na=False)]


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

tabs=st.tabs(["Database overview","Storage & formulation","Products","Suppliers & formulation","Research priorities","Compare products","Key takeaways","Data quality"])

with tabs[0]:
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
        order=["< 6.0","6.0–6.9","7.0–7.9","8.0–8.9","≥ 9.0","Not reported"]
        counts=view["pH group"].value_counts().reindex(order,fill_value=0)
        fig=go.Figure(go.Bar(x=counts.index,y=counts.values,marker_color="#5EBB79",
                             text=counts.values,textposition="outside"))
        fig.update_layout(title="pH distribution (reported vs missing)",yaxis_title="Product records")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    with right:
        counts=view.manufacturer.replace("","Unknown").value_counts()
        fig=go.Figure(go.Pie(labels=counts.index,values=counts.values,hole=.62,
                             marker_colors=PALETTE,textinfo="percent"))
        fig.update_layout(title="Suppliers / manufacturers")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    st.caption("Frozen and refrigerated categories are simplified. A record with both frozen and refrigerated temperatures is counted as frozen; see the full temperature text in Product catalog.")


    st.markdown("### Discover GlobeVAC")
    about_col,services_col=st.columns([1,1.12],gap="medium")
    with about_col:
        st.markdown("""
<div class="gv-section">
  <div class="gv-eyebrow">ABOUT US</div>
  <h2>Redefining Biologics Stability</h2>
  <p>GlobeVAC is dedicated to solving one of global health's most critical challenges: ensuring vaccines and biologics remain potent regardless of environmental conditions.</p>
  <div class="gv-item"><span class="gv-icon">◎</span><div><b>Our Mission</b><p>To make every vaccine thermostable, eliminating cold chain dependency and expanding global access to life-saving biologics.</p></div></div>
  <div class="gv-item"><span class="gv-icon">◉</span><div><b>Global Reach</b><p>Our solutions are designed for the most challenging environments — from tropical climates to remote communities with limited infrastructure.</p></div></div>
  <div class="gv-item"><span class="gv-icon">✧</span><div><b>Scientific Excellence</b><p>Backed by rigorous research and development, our proprietary formulations push the boundaries of what's possible in vaccine stability.</p></div></div>
</div>""",unsafe_allow_html=True)
    with services_col:
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

with tabs[0]:
    st.markdown("### Global cold-chain product database")
    st.write("A searchable research inventory of biologics, vaccines, proteins and antibodies, designed to connect product identities, suppliers, storage requirements and future market intelligence.")
    st.caption("Scope: the full imported CSV. The existing Storage & formulation and Products tabs focus on a narrower, formulation-qualified subset.")
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Extracted records",len(database))
    c2.metric("Distinct product IDs",database["Product ID"].nunique())
    c3.metric("Named suppliers",database.loc[database.manufacturer.map(has_value),"manufacturer"].nunique())
    c4.metric("Storage stated",int(database["Temperature available"].sum()))
    c5.metric("Source links",int(database["Source available"].sum()))
    st.markdown("#### Storage classification")
    st.caption("Storage classifications are conservative screening labels derived from extracted storage text. Mixed conditions are flagged for review. Shipping and handling requirements are not inferred.")
    left,right=st.columns(2)
    with left:
        order=["Refrigerated","Frozen","Ultra-low temperature","Other controlled temperature","Ambient","Uncertain / review needed"]
        cnt=database["Storage classification"].value_counts().reindex(order,fill_value=0)
        fig=go.Figure(go.Bar(y=cnt.index,x=cnt.values,orientation="h",marker_color=["#62B77A","#23834E","#124A35","#7CBCC0","#B2CBB8","#C9D1CD"],text=cnt.values,textposition="outside"))
        fig.update_layout(title="Storage classes across imported records",xaxis_title="Records",yaxis_title="",yaxis=dict(autorange="reversed"))
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    with right:
        cat=database["Product category"].value_counts().sort_values()
        fig=go.Figure(go.Bar(y=cat.index,x=cat.values,orientation="h",marker_color="#469A69",text=cat.values,textposition="outside"))
        fig.update_layout(title="Product categories (name-derived)",xaxis_title="Records",yaxis_title="")
        st.plotly_chart(chart_layout(fig),use_container_width=True)
    st.markdown("#### Market discovery snapshot")
    st.write("This is a **supplier and product-coverage view**, not a market-size estimate. The current CSV does not contain reliable country coverage, market demand, revenue, or shipping-temperature data.")
    supplier_stats=(database.assign(Supplier=database["manufacturer"].where(database["manufacturer"].map(has_value),"Unknown"))
        .groupby("Supplier",as_index=False)
        .agg(Records=("Product ID","size"),Products=("Product ID","nunique"),
             Storage_reported=("Temperature available","sum"),Sources_linked=("Source available","sum"))
        .sort_values(["Products","Supplier"],ascending=[False,True]))
    st.dataframe(supplier_stats.rename(columns={"Storage_reported":"Storage stated","Sources_linked":"Source linked"}),hide_index=True,use_container_width=True,height=230)
    st.markdown("#### Searchable product registry")
    search_all=st.text_input("Search the full database",placeholder="Product, supplier or protein",key="full_database_search")
    reg=database.copy()
    if search_all:
        needle=re.escape(search_all)
        reg=reg[reg["product"].str.contains(needle,case=False,na=False)|
                reg["manufacturer"].str.contains(needle,case=False,na=False)|
                reg["protein"].str.contains(needle,case=False,na=False)]
    registry=reg.rename(columns={"product":"Product","manufacturer":"Supplier",
       "storage_temperature":"Storage requirement","source":"Source URL"})
    registry_cols=["Product ID","Product","Supplier","Catalog number","Product category",
                   "Storage classification","Storage requirement","Shipping temperature",
                   "Market / country","Evidence status","Source URL"]
    st.dataframe(registry[registry_cols].fillna(""),hide_index=True,use_container_width=True,height=340,
        column_config={"Source URL":st.column_config.LinkColumn("Source URL",display_text="Open source")})
    export_csv(registry[registry_cols],"GlobeVAC_product_registry.csv","⬇ Export full product registry")
    with st.expander("Evidence, traceability and next data improvements"):
        st.markdown("""
**Current data:** original storage text, source links, buffer/pH fields and some evidence fields are preserved in the CSV. Product IDs are deterministic provisional keys, not manufacturer-issued catalog identifiers.

**To collect next:** catalog numbers, manufacturer-confirmed product IDs, product-level source citations and PDF page numbers, evidence extraction date, independent verification status, separate shipping/handling temperatures, and market/country availability.

**Priority workflow:** verify products → normalize suppliers → confirm storage classes → add shipping evidence → expand geography → integrate independently sourced market demand and commercial estimates.
""")
        st.dataframe(database[[c for c in ["Product ID","product","storage_evidence","evidence_page","evidence_category","source_type","source"] if c in database]],hide_index=True,use_container_width=True,height=220)
    st.info("A product being stored cold does not, by itself, prove that it must be shipped cold. Market opportunities and cold-chain dependency require product-specific verification.")

with tabs[1]:
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

with tabs[2]:
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


with tabs[3]:
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

with tabs[4]:
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

with tabs[5]:
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

with tabs[6]:
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
st.markdown('<p class="gv-foot">GlobeVAC · Biological Product Intelligence · Extracted data requires manufacturer validation</p>',unsafe_allow_html=True)
