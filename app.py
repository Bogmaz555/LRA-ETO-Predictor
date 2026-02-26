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
        
        # --- NOWE PARAMETRY ---
        project_duration = st.slider("Czas trwania projektu (miesiące)", 1, 24, 6)
        material_volatility = st.slider("Miesięczna zmienność cen materiałów (%)", 0.0, 3.0, 0.5, step=0.1)
        innovation_level = st.select_slider(
            "Poziom Innowacyjności (R&D)",
            options=["Standard", "Adaptacja", "Nowy projekt", "Prototyp"],
            value="Adaptacja"
        )
        inn_map = {"Standard": 0.0, "Adaptacja": 0.05, "Nowy projekt": 0.12, "Prototyp": 0.25}
        
        f = st.slider("Poziom niepewności projektowania F (%)", 0, 100, 58, key="f_gate2")
        alpha = st.slider("α (współczynnik kalibracji)", min_value=0.22, max_value=0.45, value=0.35, step=0.01)
        history_pts = st.slider("Punkty historii klienta", 0, 20, 12)

    with col2:
        # Obliczenia buforów
        buffer_g = base_cost * (f / 100) * alpha
        buffer_h = base_cost * (0.1 + history_pts / 100)
        buffer_i = base_cost * 0.10
        buffer_innovation = base_cost * inn_map[innovation_level]
        buffer_time = (base_cost * 0.6) * (material_volatility / 100) * project_duration
        
        total_cost = base_cost + buffer_g + buffer_h + buffer_i + buffer_innovation + buffer_time
        margin = (offer_value - total_cost) / offer_value * 100 if offer_value > 0 else 0
        
        advance_val = offer_value * (advance_pct / 100)

        st.metric("Całkowite koszty Gate-2", f"{total_cost:,.0f} zł")
        st.metric("Rentowność brutto", f"{margin:.1f}%", delta="GO" if margin >= 22 else "NO-GO")
        st.metric("Kwota zaliczki", f"{advance_val:,.0f} zł")

    with st.expander("🔍 Zobacz szczegółowy wykaz składowych Gate-2"):
        breakdown_df = pd.DataFrame({
            "Element kosztorysu": ["Koszt bazowy", "Bufor G (Niepewność)", "Bufor H (Historia)", "Bufor I (Narzuty)", "Innowacyjność", "Zmienność materiałów", "**SUMA GATE-2**"],
            "Wartość [zł]": [f"{base_cost:,.2f}", f"{buffer_g:,.2f}", f"{buffer_h:,.2f}", f"{buffer_i:,.2f}", f"{buffer_innovation:,.2f}", f"{buffer_time:,.2f}", f"**{total_cost:,.2f}**"],
            "Procent bazy": ["-", f"{(f*alpha):.1f}%", f"{(5+history_pts):.1f}%", "10.0%", f"{(inn_map[innovation_level]*100):.1f}%", f"{(buffer_time/base_cost*100):.1f}%", f"{(total_cost/base_cost*100-100):.1f}% więcej"]
        })
        st.table(breakdown_df)

    if st.button("🚀 Uruchom symulację Monte Carlo (10 000 iteracji)"):
        # Odchylenie rośnie z czasem i innowacyjnością
        sigma = 0.12 + (project_duration * 0.01) + (inn_map[innovation_level] * 0.4)
        sim_costs = np.random.normal(total_cost, total_cost * sigma, 10000)
        fig = px.histogram(sim_costs, nbins=80, title=f"Rozkład kosztów (Niepewność: {sigma*100:.1f}%)")
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("""
        ### 📊 Jak interpretować wynik symulacji?
        * **Kształt dzwonu:** Najwyższe słupki to scenariusze o największym prawdopodobieństwie.
        * **P85 (Cena bezpieczna):** Rekomendowany budżet dający 85% pewności dotrzymania marży.
        """)

    if margin >= 22:
        st.success("✅ GO – projekt przechodzi Gate-2")
    elif margin >= 15:
        st.warning("⚠️ WARUNKOWE – renegocjuj zakres lub zaliczki")
    else:
        st.error("❌ NO-GO – projekt poniżej progu rentowności")
    
    st.divider()
    st.subheader("💾 Zapisz projekt")
    col1, col2 = st.columns([3, 1])
    with col1:
        project_name = st.text_input("Nazwa projektu (np. 'Klient XYZ - ETO-2026')", placeholder="Wpisz nazwę...")
    with col2:
        if st.button("💾 Zapisz"):
            if project_name.strip():
                status = "GO" if margin >= 22 else ("WARUNKOWE" if margin >= 15 else "NO-GO")
                add_project(project_name, offer_value, total_cost, margin, status)
                st.success(f"✅ Projekt '{project_name}' zapisany!")

# ====================== GATE-3 + CR ======================
with tab3:
    st.header("Gate-3: Budżet wykonawczy + Change Request")
    uploaded_file = st.file_uploader("Wgraj plik BOM (Excel)", type=["xlsx"])
    col1, col2 = st.columns(2)
    with col1:
        cr_hours = st.number_input("Dodatkowe godziny (CR)", value=0)
    with col2:
        cr_materials = st.number_input("Dodatkowe materiały (zł)", value=0)
    if st.button("Oblicz koszt Change Request"):
        cr_cost = cr_hours * 110 + cr_materials
        st.success(f"Koszt CR: **{cr_cost:,.0f} zł**")

# ====================== DASHBOARD (ZGODNY Z TWOIM ORYGINAŁEM) ======================
with tab4:
    st.header("Dashboard Zarządu – Przegląd")
    projects = load_projects()
    
    if projects:
        # Metryki
        col1, col2, col3 = st.columns(3)
        go_count = len([p for p in projects if p["status"] == "GO"])
        warunkowe_count = len([p for p in projects if p["status"] == "WARUNKOWE"])
        nogo_count = len([p for p in projects if p["status"] == "NO-GO"])
        avg_margin = np.mean([p["rentowność"] for p in projects])
        
        with col1:
            st.metric("Średnia rentowność netto", f"{avg_margin:.1f}%")
        with col2:
            st.metric("Projektów GO", f"{go_count} z {len(projects)}")
        with col3:
            st.metric("Projektów NO-GO", nogo_count)
        
        # Tabela projektów
        st.subheader("📋 Lista zapisanych projektów")
        df_projects = pd.DataFrame(projects)
        df_display = df_projects[["nazwa", "wartość_oferty", "koszty_bazowe", "rentowność", "status", "data"]].copy()
        df_display.columns = ["Nazwa", "Wartość oferty (zł)", "Koszty (zł)", "Rentowność (%)", "Status", "Data"]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        # Wykresy
        col1, col2 = st.columns(2)
        with col1:
            status_counts = df_projects["status"].value_counts()
            fig_status = px.pie(values=status_counts.values, names=status_counts.index, title="Rozkład projektów wg statusu",
                                color_discrete_map={"GO": "#00D084", "WARUNKOWE": "#FFA500", "NO-GO": "#FF4444"})
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            fig_margin = px.scatter(df_projects, x="wartość_oferty", y="rentowność", color="status", size="koszty_bazowe",
                                    hover_data=["nazwa"], title="Rentowność vs Wartość oferty",
                                    color_discrete_map={"GO": "#00D084", "WARUNKOWE": "#FFA500", "NO-GO": "#FF4444"})
            fig_margin.add_hline(y=22, line_dash="dash", line_color="green", annotation_text="próg GO (22%)")
            fig_margin.add_hline(y=15, line_dash="dash", line_color="orange", annotation_text="próg WARUNKOWE (15%)")
            st.plotly_chart(fig_margin, use_container_width=True)
        
        # Usuń projekt
        st.subheader("🗑️ Zarządzanie projektami")
        col1, col2 = st.columns([3, 1])
        with col1:
            project_to_delete = st.selectbox("Wybierz projekt do usunięcia:", options=[p["nazwa"] for p in projects], key="delete_select")
        with col2:
            if st.button("🗑️ Usuń"):
                project_id = next((p["id"] for p in projects if p["nazwa"] == project_to_delete), None)
                if project_id:
                    delete_project(project_id)
                    st.success(f"✅ Projekt '{project_to_delete}' usunięty!")
                    st.rerun()
    else:
        st.info("📊 Brak zapisanych projektów. Przejdź do Gate-2 i zapisz swój pierwszy projekt!")

st.sidebar.success("Aplikacja działa poprawnie ✅")
st.sidebar.caption("LRA-ETO Predictor v2026 • Pełna wersja webowa")
st.sidebar.markdown("""
**Konta techniczne:**
- Gate-1: Ocena ryzyka RFQ
- Gate-2: Koszty + Monte Carlo
- Gate-3: Zmiana zakresu (CR)
- Dashboard: KPI zarządu
""", help="Architektura systemu bramek")
