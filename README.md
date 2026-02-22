# 🎯 LRA-ETO Predictor 2026

Warstwowy model przewidywania rentowności projektów ETO – Gate 1-2-3 + Monte Carlo

## 📋 Funkcjonalności

- **Gate-1**: Szybka selekcja ofert RFQ
- **Gate-2**: Kalkulacja kosztów + symulacja Monte Carlo
- **Gate-3**: Budżet wykonawczy i Change Request
- **Dashboard**: Metryki zarządu i zarządzanie projektami

## 🚀 Instalacja i uruchomienie

### Lokalnie

```bash
git clone https://github.com/[TWOJ_LOGIN]/LRA-ETO-Predictor.git
cd LRA-ETO-Predictor
pip install -r requirements.txt
streamlit run app.py
```

### Streamlit Cloud

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/[TWOJ_LOGIN]/LRA-ETO-Predictor/main/app.py)

## 📦 Wymagania

- Python 3.13+
- streamlit
- plotly
- pandas
- numpy
- openpyxl
- reportlab

## 💾 Dane

Projekty są zapisywane w pliku `projekty.json`

## 📝 Licencja

MIT
