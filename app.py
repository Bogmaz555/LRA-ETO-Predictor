import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import datetime
import json
import os

# ====================== FUNKCJE DO ZARZĄDZANIA PROJEKTAMI ======================
PROJEKTY_FILE = "projekty.json"

def load_projects():
    if os.path.exists(PROJEKTY_FILE):
        with open(PROJEKTY_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("projekty", [])
    return []

def save_projects(projects):
    with open(PROJEKTY_FILE, "w", encoding="utf-8") as f:
        json.dump({"projekty": projects}, f, ensure_ascii=False, indent=2)

def add_project(nazwa, offer_value, total_cost, margin, status):
    projects = load_projects()
    new_project = {
        "id": len(projects) + 1,
        "nazwa": nazwa,
        "wartość_oferty": float(offer_value),
        "koszty_bazowe": float(total_cost),
        "rentowność": round(margin, 2),
        "status": status,
        "data": datetime.date.today().isoformat()
    }
    projects.append(new_project)
    save_projects(projects)
    return new_project

def delete_project(project_id):
    projects = load_projects()
    projects = [p for p in projects if p["id"] != project_id]
    save_projects(projects)

st.set_page_config(page_title="LRA-ETO Predictor 2026", layout="wide", page_icon="🎯")

st.title("🎯 LRA-ETO Predictor 2026")
st.caption("Warstwowy model przewidywania rentowności ETO • Gate 1-2-3 + Monte Carlo")

# ====================== INSTRUKCJE W SIDEBARZ ======================
with st.sidebar:
    st.divider()
    with st.expander("📖 Instrukcja obsługi"):
        st.markdown("""
        ### Jak korzystać z aplikacji?
        **Gate-1: Szybka selekcja RFQ**
        **Gate-2: Główna kalkulacja**
        - Uwzględnij Innowacyjność i czas trwania projektu dla lepszej precyzji.
        - Dostosuj Narzuty operacyjne i Ryzyko historii klienta.
        **Gate-3: Budżet + Change Request**
        **Dashboard Zarządu**
        """)
    st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Gate-1 RFQ", "Gate-2 Koncepcja", "Gate-3 + CR", "Dashboard Zarządu"])

# ====================== GATE-1 ======================
with tab1:
    st.header("Gate-1: Szybka selekcja RFQ")
    col1, col2 = st.columns(2)
    with col1:
        offer_value = st.number_input("Wartość oferty netto (zł)", value=3200000, step=10000)
        f_quick = st.slider("Szybka ocena niepewności F (%)", 0, 100, 55)
    with col2:
        client_history = st.selectbox("Historia zmian klienta", ["0 zmian", "1 zmiana", "2+ zmian"])
        plc_load = st.slider("Obciążenie zespołu PLC/Robotyka (%)", 0, 100, 72)
        advance_pct = st.slider("Możliwa zaliczka (%)", 0, 100, 50)

    if f_quick > 60 or plc_load > 85 or client_history == "2+ zmian" or advance_pct < 45:
        st.error("⚠️ WARUNKOWE / NO-GO – zalecana płatna koncepcja")
    else:
        st.success("✅ GO – przygotuj ofertę Warstwy 1")

# ====================== GATE-2 ======================
with tab2:
    st.header("Gate-2: Główna kalkulacja po koncepcji")

    col1, col2 = st.columns([1, 1])
    with col1:
        base_cost = st.number_input("Koszty bazowe (zł)", value=2313400)
        
        # --- ROZWINIĘTE PARAMETRY ---
        overhead_pct = st.slider("Narzuty operacyjne / Overhead (%)", 0, 25, 10)
        history_risk_pct = st.slider("Ryzyko historii klienta (%)", 0, 30, 12, help="0% oznacza brak dodatkowego narzutu na historię zmian klienta")
        
        project_duration = st.slider("Czas trwania projektu (miesiące)", 1, 24, 6)
        material_volatility = st.slider("Miesięczna zmienność cen materiałów (%)", 0.0, 3.0, 0.5, step=0.1)
        
        innovation_level = st.select_slider(
            "Poziom Innowacyjności (R&D)",
            options=["Standard", "Adaptacja", "Nowy projekt", "Prototyp"],
            value="Adaptacja"
        )
        inn_map = {"Standard": 0.0, "Adaptacja": 0.05, "Nowy projekt": 0.12, "Prototyp": 0.25}
        
        f = st.slider("Poziom niepewności projektowania F (%)", 0, 100, 58, key="f_gate2")
        alpha = st.slider("α (współczynnik kalibracji)", min_value=0.10, max_value=0.50, value=0.35, step=0.01)

    with col2:
        # Obliczenia buforów
        buffer_g = base_cost * (f / 100) * alpha
        # Płynna historia klienta (bez sztywnego progu)
        buffer_h = base_cost * (history_risk_pct / 100)
        # Płynne narzuty operacyjne
        buffer_i = base_cost * (overhead_pct / 100)
        
        buffer_innovation = base_cost * inn_map[innovation_level]
        buffer_time = (base_cost * 0.6) * (material_volatility / 100) * project_duration
        
        total_cost = base_cost + buffer_g + buffer_h + buffer_i + buffer_innovation + buffer_time
        margin = (offer_value - total_cost) / offer_value * 100 if offer_value > 0 else 0
        
        advance_val = offer_value * (advance_pct / 100)

        st.metric("Całkowite koszty Gate-2", f"{total_cost:,.0f} zł")
        st.metric("Rentowność brutto", f"{margin:.1f}%", delta="GO" if margin >= 22 else "NO-GO")
        st.metric("Kwota zaliczki", f"{advance_val:,.0f} zł")

    with st.expander("🔍 Zobacz szczegółowy wykaz składowych Gate
