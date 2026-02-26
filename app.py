import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import datetime
import json
import os

# ====================== FUNKCJE DO ZARZĄDZANIA PROJEKTAMI ======================
PROJEKTY_FILE = "projekty.json"

def load_projects():
    """Ładuje listę projektów z pliku JSON"""
    if os.path.exists(PROJEKTY_FILE):
        with open(PROJEKTY_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("projekty", [])
    return []

def save_projects(projects):
    """Zapisuje listę projektów do pliku JSON"""
    with open(PROJEKTY_FILE, "w", encoding="utf-8") as f:
        json.dump({"projekty": projects}, f, ensure_ascii=False, indent=2)

def add_project(nazwa, offer_value, total_cost, margin, status):
    """Dodaje nowy projekt do listy"""
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
    """Usuwa projekt z listy"""
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
        - Wprowadź wartość oferty netto
        - Ocenij niepewność, obciążenie zespołu i historię klienta
        - Sprawdź rekomendację (GO/NO-GO)
        
        **Gate-2: Główna kalkulacja**
        - Wpisz koszty bazowe (materiały + robocizna)
        - Ustaw poziom niepewności projektowania F
        - Wybierz współczynnik kalibracji α
        - System obliczy: bufory + rentowność
        - Kliknij "🚀 Uruchom symulację" aby zobaczyć rozkład kosztów
        
        **Gate-3: Budżet + Change Request**
        - Wgraj plik BOM (Excel)
        - Dodaj godziny i materiały z Change Request
        - System obliczy dodatkowy koszt
        
        **Dashboard Zarządu**
        - Przegląd kluczowych metryk
        - Stożek niepewności przez bramki
        
        ### Interpretacja wyników:
        - 🟢 **Rentowność ≥22%** = GO (przychód > 22% wartości oferty)
        - 🟡 **Rentowność 15-22%** = WARUNKOWE (renegocjuj)
        - 🔴 **Rentowność <15%** = NO-GO (poniżej progu)
        """)
    
    st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["Gate-1 RFQ", "Gate-2 Koncepcja", "Gate-3 + CR", "Dashboard Zarządu"])

offer_value = 3200000  # globalna wartość do użycia w wszystkich tabach

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
        advance = st.slider("Możliwa zaliczka (%)", 0, 100, 50)

    if f_quick > 60 or plc_load > 85 or client_history == "2+ zmian" or advance < 45:
        st.error("⚠️ WARUNKOWE / NO-GO – zalecana płatna koncepcja")
    else:
        st.success("✅ GO – przygotuj ofertę Warstwy 1")

# ====================== GATE-2 ======================
with tab2:
    st.header("Gate-2: Główna kalkulacja po koncepcji")

    col1, col2 = st.columns([1, 1])
    with col1:
        base_cost = st.number_input("Koszty bazowe (zł)", value=2313400)
        f = st.slider("Poziom niepewności projektowania F (%)", 0, 100, 58, key="f_gate2")
        alpha = st.slider("α (współczynnik kalibracji)", min_value=0.22, max_value=0.45, value=0.35, step=0.01)
        history_pts = st.slider("Punkty historii klienta", 0, 20, 12)

    with col2:
        # Obliczenia buforów (Twoja oryginalna logika)
        buffer_g = base_cost * (f / 100) * alpha
        buffer_h = base_cost * (0.18 + history_pts / 100)
        buffer_i = base_cost * 0.10
        total_cost = base_cost + buffer_g + buffer_h + buffer_i
        margin = (offer_value - total_cost) / offer_value * 100 if offer_value > 0 else 0

        st.metric("Całkowite koszty Gate-2", f"{total_cost:,.0f} zł")
        st.metric("Rentowność brutto", f"{margin:.1f}%", delta="GO" if margin >= 22 else "NO-GO")

    # --- NOWA FUNKCJA: SZCZEGÓŁOWY WYKAZ KOSZTÓW ---
    with st.expander("🔍 Zobacz szczegółowy wykaz składowych Gate-2"):
        breakdown_df = pd.DataFrame({
            "Element kosztorysu": ["Koszt bazowy", "Bufor G (Niepewność F)", "Bufor H (Historia klienta)", "Bufor I (Narzuty stałe)", "**SUMA GATE-2**"],
            "Wartość [zł]": [
                f"{base_cost:,.2f}",
                f"{buffer_g:,.2f}",
                f"{buffer_h:,.2f}",
                f"{buffer_i:,.2f}",
                f"**{total_cost:,.2f}**"
            ],
            "Procent bazy": [
                "-",
                f"{(f * alpha):.1f}%",
                f"{(18 + history_pts):.1f}%",
                "10.0%",
                f"{((total_cost/base_cost - 1) * 100):.1f}% więcej"
            ]
        })
        st.table(breakdown_df)

    # Monte Carlo
    if st.button("🚀 Uruchom symulację Monte Carlo (10 000 iteracji)"):
        sim_costs = np.random.normal(total_cost, total_cost * 0.15, 10000)
        fig = px.histogram(sim_costs, nbins=80, title="Rozkład kosztów – P85 = bezpieczna cena")
        st.plotly_chart(fig, use_container_width=True)
        
        # --- NOWA FUNKCJA: WYJAŚNIENIE WYKRESU ---
        st.markdown("""
        ### 📊 Jak interpretować wynik symulacji?
        Wykres powyżej przedstawia **10 000 wariantów** wykonania tego projektu:
        * **Kształt dzwonu:** Najwyższe słupki to scenariusze o największym prawdopodobieństwie. Twój koszt **Gate-2** znajduje się w centrum tego dzwonu.
        * **Ogon po prawej stronie:** Pokazuje scenariusze pesymistyczne (nieprzewidziane awarie, błędy projektowe).
        * **P85 (Cena bezpieczna):** Zazwyczaj rekomenduje się przyjęcie budżetu na poziomie 85-tego percentyla (miejsce, gdzie 85% słupków jest po lewej stronie). Daje to 85% pewności, że nie przekroczysz założonej kwoty.
        """)

    if margin >= 22:
        st.success("✅ GO – projekt przechodzi Gate-2")
    elif margin >= 15:
        st.warning("⚠️ WARUNKOWE – renegocjuj zakres lub zaliczki")
    else:
        st.error("❌ NO-GO – projekt poniżej progu rentowności")
    
    # ===== Sekcja zapisu projektu =====
    st.divider()
    st.subheader("💾 Zapisz projekt")
    col1, col2 = st.columns([3, 1])
    with col1:
        project_name = st.text_input("Nazwa projektu (np. 'Klient XYZ - ETO-2026')", placeholder="Wpisz nazwę...")
    with col2:
        if st.button("💾 Zapisz"):
            if project_name.strip():
                if margin >= 22:
                    status = "GO"
                elif margin >= 15:
                    status = "WARUNKOWE"
                else:
                    status = "NO-GO"
                
                add_project(project_name, offer_value, total_cost, margin, status)
                st.success(f"✅ Projekt '{project_name}' zapisany!")
            else:
                st.error("⚠️ Wpisz nazwę projektu")

# ====================== GATE-3 + CR ======================
with tab3:
    st.header("Gate-3: Budżet wykonawczy + Change Request")
    uploaded_file = st.file_uploader("Wgraj plik BOM (Excel)", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.dataframe(df.head(), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        cr_hours = st.number_input("Dodatkowe godziny (CR)", value=0)
    with col2:
        cr_materials = st.number_input("Dodatkowe materiały (zł)", value=0)

    if st.button("Oblicz koszt Change Request"):
        cr_cost = cr_hours * 110 + cr_materials
        st.success(f"Koszt CR: **{cr_cost:,.0f} zł**")

# ====================== DASHBOARD ======================
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
            fig_status = px.pie(
                values=status_counts.values, 
                names=status_counts.index,
                title="Rozkład projektów wg statusu",
                color_discrete_map={"GO": "#00D084", "WARUNKOWE": "#FFA500", "NO-GO": "#FF4444"}
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        with col2:
            fig_margin = px.scatter(
                df_projects,
                x="wartość_oferty",
                y="rentowność",
                color="status",
                size="koszty_bazowe",
                hover_data=["nazwa"],
                title="Rentowność vs Wartość oferty",
                color_discrete_map={"GO": "#00D084", "WARUNKOWE": "#FFA500", "NO-GO": "#FF4444"}
            )
            fig_margin.add_hline(y=22, line_dash="dash", line_color="green", annotation_text="próg GO (22%)")
            fig_margin.add_hline(y=15, line_dash="dash", line_color="orange", annotation_text="próg WARUNKOWE (15%)")
            st.plotly_chart(fig_margin, use_container_width=True)
        
        # Usuń projekt
        st.subheader("🗑️ Zarządzanie projektami")
        col1, col2 = st.columns([3, 1])
        with col1:
            project_to_delete = st.selectbox(
                "Wybierz projekt do usunięcia:",
                options=[p["nazwa"] for p in projects],
                key="delete_select"
            )
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
st.sidebar.divider()
st.sidebar.markdown("""
**Konta techniczne:**
- Gate-1: Ocena ryzyka RFQ
- Gate-2: Koszty + Monte Carlo  
- Gate-3: Zmiana zakresu (CR)
- Dashboard: KPI zarządu
""", help="Architektura systemu bramek")
