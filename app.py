"""Multimodal Construction Intelligence Platform - Skill Wallet Capstone Project 1.

Run locally:  streamlit run app.py
Deploy:       push app.py + requirements.txt to GitHub, then Streamlit Community Cloud.
"""
import json
import urllib.parse

import streamlit as st
from PIL import Image

try:
    from google import genai
    from google.genai import types
    GENAI_OK = True
except ImportError:  # app still runs in demo mode
    GENAI_OK = False

MODEL = "gemini-2.5-flash"

st.set_page_config(page_title="Construction Intelligence Platform", page_icon="🏗️", layout="wide")

# ---------------------------------------------------------------- styling
st.markdown("""
<style>
.hero{background:linear-gradient(135deg,#0f2027,#203a43,#f2994a);padding:1.4rem 1.8rem;
border-radius:14px;color:#fff;margin-bottom:1rem}
.hero h1{margin:0;font-size:1.9rem;color:#fff} .hero p{margin:.3rem 0 0;opacity:.9}
.card{background:#fff;border:1px solid #e6e8ec;border-left:5px solid #f2994a;border-radius:10px;
padding:.9rem 1.1rem;box-shadow:0 1px 4px rgba(0,0,0,.06);color:#1f2937}
.card .lbl{font-size:.75rem;text-transform:uppercase;letter-spacing:.05em;color:#6b7280}
.card .val{font-size:1.6rem;font-weight:700}
.pill{display:inline-block;padding:.2rem .75rem;border-radius:999px;font-weight:600;font-size:.82rem;color:#fff}
.p-ok{background:#16a34a}.p-warn{background:#d97706}.p-bad{background:#dc2626}.p-crit{background:#7f1d1d}
.p-low{background:#2563eb}
.alert{border-radius:10px;padding:.8rem 1rem;margin:.4rem 0;border-left:5px solid #dc2626;
background:#fef2f2;color:#1f2937}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers
def card(label: str, value: str) -> str:
    return f'<div class="card"><div class="lbl">{label}</div><div class="val">{value}</div></div>'


def pill(text: str) -> str:
    t = str(text).lower()
    cls = ("p-crit" if "critical" in t else "p-bad" if any(k in t for k in ("high", "non", "fail", "immediate", "structural"))
           else "p-warn" if any(k in t for k in ("medium", "partial", "moderate", "soon")) 
           else "p-low" if "low" in t else "p-ok")
    return f'<span class="pill {cls}">{text}</span>'


def inr(amount: float) -> str:
    """Format a rupee amount as Crores / Lakhs."""
    if amount >= 1e7:
        return f"₹ {amount / 1e7:,.2f} Cr"
    return f"₹ {amount / 1e5:,.2f} Lakhs"


def get_client():
    key = st.session_state.get("api_key", "")
    if key and GENAI_OK:
        try:
            return genai.Client(api_key=key)
        except Exception as exc:
            st.sidebar.error(f"Client error: {exc}")
    return None


def gemini_json(prompt: str, image: Image.Image) -> dict:
    client = get_client()
    resp = client.models.generate_content(
        model=MODEL, contents=[prompt, image],
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
    text = (resp.text or "").strip().removeprefix("```json").removesuffix("```").strip()
    return json.loads(text)


def gemini_text(prompt: str, system: str) -> str:
    client = get_client()
    resp = client.models.generate_content(
        model=MODEL, contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system, temperature=0.4))
    return resp.text or "(no response)"


def load_image(upload) -> Image.Image:
    img = Image.open(upload).convert("RGB")
    img.thumbnail((1600, 1600))
    return img


# ---------------------------------------------------------------- prompts & demo data
PPE_PROMPT = """You are a certified construction safety officer auditing a site photo against OSHA 1926
and Indian standards (IS 456 for concrete works, BOCW Act, IS 4130 for demolition/site safety).
Check worker PPE: helmets, high-visibility vests, steel-toe boots, safety harnesses (for work at height).
Return ONLY JSON with this schema:
{"safety_score": int 0-100, "overall_status": "Compliant|Partially Compliant|Non-Compliant",
 "workers_detected": int,
 "ppe_detection": {"helmet": "Present|Absent|Not Visible", "high_vis_vest": "...", "steel_toe_boots": "...", "safety_harness": "..."},
 "hazards": [{"hazard": str, "severity": "Low|Medium|High|Critical", "standard_reference": str, "remedy": str}],
 "summary": str}
Only report what is visible; use "Not Visible" when unsure."""

CRACK_PROMPT = """You are a structural engineer inspecting a concrete/masonry surface photo per IS 456 and IS 15988.
Classify the defect as one of: Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling.
Return ONLY JSON:
{"defect_type": str, "confidence": int 0-100, "estimated_crack_width_mm": float,
 "pattern_description": str, "root_causes": [str], "recommended_repairs": [str],
 "urgency": "Low|Medium|High|Immediate", "monitoring_advice": str,
 "disclaimer": "Visual estimate only; confirm with on-site NDT."}
Repairs should reference methods such as epoxy injection, structural re-grouting, polymer-modified mortar, jacketing."""

DEMO_PPE = {
    "safety_score": 62, "overall_status": "Partially Compliant", "workers_detected": 3,
    "ppe_detection": {"helmet": "Present", "high_vis_vest": "Present", "steel_toe_boots": "Absent", "safety_harness": "Absent"},
    "hazards": [
        {"hazard": "Worker at height without harness", "severity": "Critical", "standard_reference": "OSHA 1926.501",
         "remedy": "Stop work; issue full-body harness anchored to a rated lifeline."},
        {"hazard": "Open footwear on rebar-laden deck", "severity": "High", "standard_reference": "OSHA 1926.96",
         "remedy": "Mandate IS 15298 safety shoes with steel toe at site gate."},
        {"hazard": "Unprotected slab edge", "severity": "Medium", "standard_reference": "OSHA 1926.502",
         "remedy": "Install double-rail guardrails and toe boards."}],
    "summary": "[DEMO] Head and visibility protection in place; fall protection and footwear need immediate correction."}

DEMO_CRACK = {
    "defect_type": "Settlement", "confidence": 78, "estimated_crack_width_mm": 3.5,
    "pattern_description": "Diagonal stair-step crack, wider at the top, indicating differential foundation movement.",
    "root_causes": ["Differential soil settlement", "Poor compaction under plinth", "Nearby water leakage softening subgrade"],
    "recommended_repairs": ["Underpin/stabilise foundation via grouting", "Epoxy injection for cracks >0.3 mm",
                            "Structural re-grouting with non-shrink grout", "Re-plaster with polymer-modified mortar"],
    "urgency": "High", "monitoring_advice": "Install tell-tale gauges; review monthly for 6 months.",
    "disclaimer": "[DEMO] Visual estimate only; confirm with on-site NDT."}

WEATHER = {
    "Normal": {"icon": "☀️", "alerts": ["Standard PPE and toolbox talk at shift start.", "Maintain routine curing: wet-cure concrete for at least 7 days (IS 456)."]},
    "High Wind": {"icon": "💨", "alerts": [
        "SUSPEND crane and hoist operations when sustained wind exceeds ~36 km/h (per manufacturer limits).",
        "Secure scaffolding sheets, formwork panels and loose materials.",
        "Stop work at height; lower and lock tower-crane booms into weathervane mode."]},
    "Heavy Rain": {"icon": "🌧️", "alerts": [
        "ELECTRICAL HAZARD: de-energise temporary panels, use ELCB/RCCB, keep cables off wet ground.",
        "Cover freshly poured concrete with tarpaulin; avoid pours during heavy rain.",
        "Pump out excavations; check shoring and trench walls for collapse risk.",
        "Slip hazard on ramps and scaffolds: install anti-skid treads."]},
    "Extreme Heat": {"icon": "🔥", "alerts": [
        "Concrete curing protocol: pour early morning/night, use chilled water or ice, wet-cure with fogging and burlap.",
        "Enforce hydration breaks (ORS) every 45-60 min; shift heavy work out of 12-3 PM.",
        "Watch for heat stroke symptoms; provide shaded rest areas.",
        "Re-tighten and inspect formwork: thermal expansion can shift joints."]},
}

STRUCTURES = {  # base construction cost INR/sqft, steel kg/sqft, cement bags/sqft
    "RCC Framed (Residential)": (1800, 4.0, 0.45),
    "Load-Bearing Masonry": (1500, 2.0, 0.40),
    "Steel / PEB Structure": (2200, 7.0, 0.20),
    "Luxury Villa (RCC)": (3000, 4.5, 0.50),
    "Commercial RCC Complex": (2600, 5.0, 0.48)}
TIERS = {  # (cost multiplier, market value INR/sqft)
    "Tier 1 (Mumbai, Delhi, Bengaluru)": (1.25, 9500),
    "Tier 2 (Bhopal, Indore, Jaipur)": (1.0, 5500),
    "Tier 3 (Raisen, Sagar, smaller towns)": (0.82, 3200)}
MILESTONES = [(10, "Site prep & excavation"), (25, "Foundation & plinth"), (50, "RCC superstructure"),
              (70, "Masonry & MEP rough-in"), (90, "Finishing & fixtures"), (100, "Handover")]

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("🏗️ Control Panel")
    key = st.text_input("Google Gemini API Key", type="password", placeholder="AIza...",
                        help="Stored only in this session. Leave blank for demo mode.")
    st.session_state["api_key"] = key.strip()
    LIVE = bool(key.strip()) and GENAI_OK
    if LIVE:
        st.success("Live mode: Gemini connected")
    else:
        st.info("Demo mode: sample outputs shown (no key supplied)." if GENAI_OK
                else "google-genai not installed; running in demo mode.")
    st.divider()
    st.subheader("Architecture")
    st.markdown("""
- **UI:** Streamlit
- **Vision/LLM:** Gemini multimodal (`%s`)
- **Structured output:** JSON mode
- **Valuation:** rule-based engine
- **Rendering:** Pollinations AI
- **State:** `st.session_state` (no DB)
""" % MODEL)
    st.subheader("Modules")
    st.markdown("1. Safety & PPE Audit\n2. Crack Diagnostics\n3. Planning & Valuation\n4. Site Assistant")
    st.caption("Skill Wallet Capstone · Project 1")

st.markdown('<div class="hero"><h1>🏗️ Multimodal Construction Intelligence Platform</h1>'
            '<p>AI-driven safety audits, structural diagnostics, valuation and site advisory.</p></div>',
            unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🦺 Safety & PPE Audit", "🧱 Crack Diagnostics",
                                  "💰 Planning & Valuation", "🌦️ Site Assistant"])


def run_analysis(prompt, upload, demo, label):
    """Shared multimodal analysis runner. Returns dict or None."""
    img = load_image(upload)
    st.image(img, caption=label, use_container_width=True)
    if not LIVE:
        st.warning("Demo mode: showing a sample result, not an analysis of your image.")
        return demo
    with st.spinner("Gemini is analysing the image..."):
        try:
            return gemini_json(prompt, img)
        except json.JSONDecodeError:
            st.error("The model returned malformed JSON. Please retry.")
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
    return None


# ---------------------------------------------------------------- tab 1
with tab1:
    st.subheader("Site Safety & PPE Compliance Audit")
    up = st.file_uploader("Upload a construction site photo", type=["jpg", "jpeg", "png"], key="ppe_up")
    if up and st.button("Run safety audit", type="primary", key="ppe_btn"):
        try:
            st.session_state["ppe"] = run_analysis(PPE_PROMPT, up, DEMO_PPE, "Site photo")
        except Exception as exc:
            st.error(f"Could not read image: {exc}")
    r = st.session_state.get("ppe")
    if r:
        c = st.columns(3)
        c[0].markdown(card("Safety Score", f"{r.get('safety_score', 0)} / 100"), unsafe_allow_html=True)
        c[1].markdown(card("Overall Status", pill(r.get("overall_status", "N/A"))), unsafe_allow_html=True)
        c[2].markdown(card("Workers Detected", str(r.get("workers_detected", "-"))), unsafe_allow_html=True)
        st.progress(max(0, min(100, int(r.get("safety_score", 0)))) / 100)
        st.markdown("#### PPE Checklist")
        ppe = r.get("ppe_detection", {})
        cols = st.columns(max(1, len(ppe)))
        for col, (k, v) in zip(cols, ppe.items()):
            col.markdown(f"**{k.replace('_', ' ').title()}**<br>{pill(v)}", unsafe_allow_html=True)
        st.markdown("#### Identified Hazards")
        for h in r.get("hazards", []):
            with st.expander(f"{h.get('hazard')}  ·  {h.get('severity')}"):
                st.markdown(pill(h.get("severity", "")), unsafe_allow_html=True)
                st.write(f"**Reference:** {h.get('standard_reference', '-')}")
                st.write(f"**Remedy:** {h.get('remedy', '-')}")
        st.info(r.get("summary", ""))
        st.download_button("⬇️ Download JSON report", json.dumps(r, indent=2),
                           "safety_audit_report.json", "application/json")

# ---------------------------------------------------------------- tab 2
with tab2:
    st.subheader("Crack Diagnostics & Structural Integrity")
    up = st.file_uploader("Upload a concrete / wall surface photo", type=["jpg", "jpeg", "png"], key="crk_up")
    if up and st.button("Diagnose defect", type="primary", key="crk_btn"):
        try:
            st.session_state["crack"] = run_analysis(CRACK_PROMPT, up, DEMO_CRACK, "Surface under inspection")
        except Exception as exc:
            st.error(f"Could not read image: {exc}")
    r = st.session_state.get("crack")
    if r:
        c = st.columns(4)
        c[0].markdown(card("Defect Type", r.get("defect_type", "-")), unsafe_allow_html=True)
        c[1].markdown(card("Crack Width", f"{r.get('estimated_crack_width_mm', '-')} mm"), unsafe_allow_html=True)
        c[2].markdown(card("Confidence", f"{r.get('confidence', '-')}%"), unsafe_allow_html=True)
        c[3].markdown(card("Urgency", pill(r.get("urgency", "-"))), unsafe_allow_html=True)
        st.write("")
        st.write(f"**Pattern:** {r.get('pattern_description', '-')}")
        a, b = st.columns(2)
        with a:
            st.markdown("#### Root Causes")
            for x in r.get("root_causes", []):
                st.markdown(f"- {x}")
        with b:
            st.markdown("#### Recommended Repairs")
            for x in r.get("recommended_repairs", []):
                st.markdown(f"- {x}")
        st.write(f"**Monitoring:** {r.get('monitoring_advice', '-')}")
        st.caption(r.get("disclaimer", ""))
        st.download_button("⬇️ Download JSON report", json.dumps(r, indent=2),
                           "crack_diagnosis.json", "application/json")

# ---------------------------------------------------------------- tab 3
with tab3:
    st.subheader("Planning & Real Estate Valuation")
    c1, c2 = st.columns(2)
    stype = c1.selectbox("Structure type", list(STRUCTURES))
    tier = c2.selectbox("Location tier", list(TIERS))
    area = c1.number_input("Built-up area (sqft)", 200, 200000, 1500, 50)
    pct = c2.slider("Completion (%)", 0, 100, 40)

    rate, steel_kg, cement_bags = STRUCTURES[stype]
    mult, market = TIERS[tier]
    budget = area * rate * mult
    spent = budget * pct / 100
    # Market value ramps with completion; land+approvals give a 30% floor once started.
    asset = area * market * (0.3 + 0.7 * pct / 100) if pct > 0 else 0

    m = st.columns(4)
    m[0].markdown(card("Total Budget", inr(budget)), unsafe_allow_html=True)
    m[1].markdown(card("CapEx Incurred", inr(spent)), unsafe_allow_html=True)
    m[2].markdown(card("Current Asset Value", inr(asset)), unsafe_allow_html=True)
    m[3].markdown(card("Value at Completion", inr(area * market)), unsafe_allow_html=True)
    st.write("")
    s = st.columns(4)
    s[0].markdown(card("Steel Required", f"{area * steel_kg / 1000:,.1f} MT"), unsafe_allow_html=True)
    s[1].markdown(card("Cement Required", f"{area * cement_bags:,.0f} bags"), unsafe_allow_html=True)
    s[2].markdown(card("Steel Consumed", f"{area * steel_kg * pct / 100000:,.1f} MT"), unsafe_allow_html=True)
    s[3].markdown(card("Cement Consumed", f"{area * cement_bags * pct / 100:,.0f} bags"), unsafe_allow_html=True)

    st.markdown("#### Milestone Progress")
    st.progress(pct / 100)
    cur = next((n for p, n in MILESTONES if pct <= p), "Handover")
    st.write(f"Current phase: **{cur}**")
    st.dataframe([{"Milestone": n, "Target %": p, "Status": "✅ Done" if pct >= p else "⏳ Pending"}
                  for p, n in MILESTONES], hide_index=True, use_container_width=True)
    st.caption("Estimates are indicative rule-of-thumb figures, not a substitute for a Quantity Surveyor's BOQ "
               "or a registered valuer's report.")

    st.markdown("#### 🎨 Conceptual 3D Architectural Rendering")
    style = st.text_input("Style notes", "modern minimalist, glass facade, landscaped garden, golden hour")
    prompt = (f"3D architectural rendering of a {stype.split('(')[0].strip().lower()} building, {int(area)} sqft, "
              f"Indian context, {style}, photorealistic, 8k")
    st.code(prompt, language=None)
    if st.button("Generate rendering"):
        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1024&height=640&nologo=true"
        st.image(url, caption="Conceptual render (Pollinations AI)", use_container_width=True)

# ---------------------------------------------------------------- tab 4
with tab4:
    st.subheader("Daily Site Assistant & Weather-Aware Advisory")
    cond = st.radio("Today's weather condition", list(WEATHER), horizontal=True)
    w = WEATHER[cond]
    st.markdown(f"### {w['icon']} {cond} Advisory")
    for a in w["alerts"]:
        st.markdown(f'<div class="alert">⚠️ {a}</div>' if cond != "Normal"
                    else f'<div class="alert" style="border-color:#16a34a;background:#f0fdf4">✅ {a}</div>',
                    unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 💬 Construction Engineering Assistant")
    SYSTEM = ("You are a senior civil/construction engineer assisting an Indian site team. Cite IS codes "
              "(IS 456, IS 800, IS 875, IS 1200) and OSHA where relevant. Be concise and practical. "
              f"Today's weather condition is: {cond}. Flag safety risks. Recommend a qualified engineer "
              "for load-bearing or legal decisions.")
    if "chat" not in st.session_state:
        st.session_state.chat = [{"role": "assistant",
                                  "content": "Hi! Ask me about concrete mix, curing, scheduling, safety or materials."}]
    for msg in st.session_state.chat:
        st.chat_message(msg["role"]).write(msg["content"])

    def demo_reply(q: str) -> str:
        q = q.lower()
        if "cur" in q or "concrete" in q:
            return "[DEMO] Wet-cure for at least 7 days (10 for blended cements) per IS 456. In hot weather, shade, fog and cover with wet burlap."
        if "steel" in q or "rebar" in q:
            return "[DEMO] Use Fe500D TMT bars, maintain cover per IS 456 (e.g. 25 mm columns, 20 mm slabs, 40 mm footings) and check lap lengths."
        if "safety" in q or "ppe" in q:
            return "[DEMO] Mandatory: helmet, hi-vis vest, safety shoes; harness above 1.8 m (OSHA 1926.501). Hold a daily toolbox talk."
        return "[DEMO] Add a Gemini API key in the sidebar for a full AI answer. Meanwhile, try asking about curing, steel or safety."

    if q := st.chat_input("Ask a site question..."):
        st.session_state.chat.append({"role": "user", "content": q})
        st.chat_message("user").write(q)
        if LIVE:
            history = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in st.session_state.chat[-12:])
            try:
                with st.spinner("Thinking..."):
                    ans = gemini_text(history + "\nASSISTANT:", SYSTEM)
            except Exception as exc:
                ans = f"⚠️ Request failed: {exc}"
        else:
            ans = demo_reply(q)
        st.session_state.chat.append({"role": "assistant", "content": ans})
        st.chat_message("assistant").write(ans)
    if st.button("Clear chat"):
        del st.session_state["chat"]
        st.rerun()
