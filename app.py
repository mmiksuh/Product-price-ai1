import base64, io, json, os, statistics, re
from pathlib import Path
import pandas as pd
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Product Price AI", page_icon="📷", layout="wide")
st.title("📷 Product Price AI")
st.caption("Kuvan perusteella tunnistaminen + hintatutkimus + Excel-vienti")

api_key = st.sidebar.text_input("OPENAI_API_KEY", type="password",
                                value=os.getenv("OPENAI_API_KEY", ""))
model = st.sidebar.text_input("Mallin nimi", value="gpt-5.6-luna")
if not api_key:
    st.info("Syötä OpenAI API-avain vasemmalle aloittaaksesi.")
    st.stop()

client = OpenAI(api_key=api_key)

files = st.file_uploader("Lataa 1–5 kuvaa tuotteesta", type=["jpg","jpeg","png","webp"],
                         accept_multiple_files=True)
asking = st.number_input("Ostohinta / myyjän pyytämä hinta (€)", min_value=0.0, value=0.0, step=1.0)
extra = st.text_input("Lisätieto (esim. koko, paikkakunta, kunto)", "")

def img_data(f):
    raw = f.read()
    mime = f.type or "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"

if st.button("🔎 Tunnista ja arvioi", type="primary", disabled=not files):
    content = [{
        "type": "input_text",
        "text": """Tunnista kuvissa oleva tuote mahdollisimman tarkasti. Etsi kuvasta brändi,
malli, mallinumero/SKU, koko, väri ja näkyvät kunnon merkit. Tee ensin tunnistus.
Jos jokin tieto ei ole varma, merkitse confidence pieneksi äläkä keksi sitä.
Palauta JSON seuraavassa muodossa:
{
 "brand": "", "product_name": "", "model": "", "sku": "",
 "category": "", "size": "", "color": "", "condition": "",
 "condition_notes": "", "identification_confidence": 0.0,
 "search_query": ""
}
Lisätieto käyttäjältä: """ + extra
    }]
    for f in files:
        content.append({"type":"input_image","image_url":img_data(f)})

    with st.spinner("Tunnistetaan tuotetta…"):
        r = client.responses.create(
            model=model,
            input=[{"role":"user","content":content}],
            text={"format":{"type":"json_object"}}
        )
    product = json.loads(r.output_text)

    st.subheader("Tunnistus")
    st.json(product)

    st.subheader("Hintatutkimus")
    search_prompt = f"""
Olet jälleenmyyntihinnoittelija. Tuote:
{json.dumps(product, ensure_ascii=False)}
Etsi verkosta mahdollisimman relevantteja nykyisiä ja toteutuneita vertailuhintoja.
Erota pyyntihinnat ja toteutuneet myyntihinnat. Älä keksi lähteitä tai hintoja.
Suosi samaa mallia/SKU:ta ja samaa kokoa; jos niitä ei löydy, käytä mahdollisimman
läheisiä verrokkeja. Huomioi kunto. Palauta JSON:
{{
 "comparables":[
   {{"source":"","url":"","title":"","price_eur":0,"sale_type":"asking_or_sold",
     "condition":"","size":"","match_quality":0.0}}
 ],
 "estimated_value_eur":0,
 "low_eur":0,
 "high_eur":0,
 "recommended_listing_eur":0,
 "confidence":0.0,
 "method_notes":""
}}
"""
    with st.spinner("Haetaan vertailuhintoja…"):
        r2 = client.responses.create(
            model=model,
            tools=[{"type":"web_search_preview"}],
            input=search_prompt
        )
    try:
        valuation = json.loads(r2.output_text)
    except Exception:
        st.error("Hintatutkimuksen JSON ei ollut luettavassa muodossa.")
        st.code(r2.output_text)
        st.stop()

    comps = valuation.get("comparables", [])
    prices = [float(x["price_eur"]) for x in comps if isinstance(x.get("price_eur"), (int,float)) and x["price_eur"] > 0]
    est = float(valuation.get("estimated_value_eur") or (statistics.median(prices) if prices else 0))
    rec = float(valuation.get("recommended_listing_eur") or est)

    fees = st.number_input("Arvioidut myyntikulut (€)", min_value=0.0, value=10.0, step=1.0)
    profit = rec - asking - fees
    roi = (profit / asking * 100) if asking else None

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Arvioitu arvo", f"{est:.2f} €")
    c2.metric("Suositeltu pyynti", f"{rec:.2f} €")
    c3.metric("Arvioitu voitto", f"{profit:.2f} €" if asking else "—")
    c4.metric("ROI", f"{roi:.0f} %" if roi is not None else "—")

    st.subheader("Vertailuhinnat")
    if comps:
        df = pd.DataFrame(comps)
        st.dataframe(df, use_container_width=True)
    st.write("**Luottamus:**", f"{float(valuation.get('confidence',0))*100:.0f} %")
    st.write(valuation.get("method_notes",""))

    row = {
        "Brändi": product.get("brand",""),
        "Tuote": product.get("product_name",""),
        "Malli": product.get("model",""),
        "SKU": product.get("sku",""),
        "Kategoria": product.get("category",""),
        "Koko": product.get("size",""),
        "Väri": product.get("color",""),
        "Kunto": product.get("condition",""),
        "Ostohinta €": asking,
        "Arvio €": est,
        "Suositeltu myyntihinta €": rec,
        "Kulut €": fees,
        "Voitto €": profit if asking else "",
        "ROI %": roi if roi is not None else "",
        "Luottamus %": float(valuation.get("confidence",0))*100
    }
    out = pd.DataFrame([row])
    xlsx = io.BytesIO()
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        out.to_excel(writer, index=False, sheet_name="Arvio")
        if comps:
            pd.DataFrame(comps).to_excel(writer, index=False, sheet_name="Vertailuhinnat")
    st.download_button("📊 Lataa Excel", xlsx.getvalue(),
                       file_name="tuotteen_hinta-arvio.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")