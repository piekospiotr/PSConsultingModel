import streamlit as st
import pandas as pd

# --- Definicje Funkcji Modelu Biznesowego ---

def get_default_inputs():
    """Zwraca słownik z domyślnymi parametrami wejściowymi modelu."""
    return {
        # Parametry Konsultanta
        'konsultant_godziny_pracy_miesiac': 150,
        'konsultant_stawka_billable_godz': 500.0,
        'konsultant_wynagrodzenie_roczne': 500000.0,
        'konsultant_procent_czasu_rozwoj_admin': 0.05,
        'konsultant_procent_czasu_billable_docelowy': 0.60,
        'konsultant_procent_czasu_utrzymanie_projektow': 0.15,
        # 'konsultant_procent_czasu_sprzedaz_docelowy' - obliczane dynamicznie

        # Parametry Ramp-up
        'rampup_dlugosc_lata': 2, # Informacyjnie, logika sztywno na R1, R2, Full
        'rampup_efektywnosc_billable_rok1': 0.25,
        'rampup_efektywnosc_billable_rok2': 0.60,
        'rampup_efektywnosc_sprzedaz_rok1': 0.10,
        'rampup_efektywnosc_sprzedaz_rok2': 0.50,

        # Parametry Sprzedażowe
        'sprzedaz_leady_rocznie_docelowo': 6,
        'sprzedaz_srednia_wartosc_kontraktu': 2000000.0,
        'sprzedaz_cykl_sprzedazy_miesiace': 12, # Wpływa na roczne opóźnienie
        'sprzedaz_wspolczynnik_konwersji': 0.35,

        # Parametry Korporacyjne
        'korporacyjne_overhead_roczny_na_konsultanta': 120000.0,
        'korporacyjne_koszt_rekrutacji_konsultanta': 100000.0,

        # Cele Firmy (do porównania)
        'cel_marza_operacyjna': 0.15,
        'cel_liczba_konsultantow_docelowa': 7, # Informacyjnie
        'cel_obrot_roczny_aspiracja': 100000000.0, # Informacyjnie

        # Parametry Modelu
        'model_horyzont_analizy_lata': 5,

        # Plan Rekrutacji (Nowi Konsultanci w Roku)
        'rekrutacja_rok1_nowi': 2,
        'rekrutacja_rok2_nowi': 2,
        'rekrutacja_rok3_nowi': 3,
        'rekrutacja_rok4_nowi': 0,
        'rekrutacja_rok5_nowi': 0,
    }

def calculate_consultant_annual_metrics(inputs_dict):
    """Oblicza roczne metryki dla każdego typu konsultanta (R1, R2, Full)."""
    metrics = {}
    godziny_pracy_rocznie_global = inputs_dict['konsultant_godziny_pracy_miesiac'] * 12

    for typ in ["R1", "R2", "Full"]:
        m = {}
        m['godziny_pracy_rocznie'] = godziny_pracy_rocznie_global
        m['godziny_na_rozwoj_admin'] = m['godziny_pracy_rocznie'] * inputs_dict['konsultant_procent_czasu_rozwoj_admin']

        if typ == "R1":
            efektywnosc_billable = inputs_dict['rampup_efektywnosc_billable_rok1']
            efektywnosc_sprzedaz = inputs_dict['rampup_efektywnosc_sprzedaz_rok1']
            m['godziny_na_utrzymanie_projektow'] = 0 # Założenie
        elif typ == "R2":
            efektywnosc_billable = inputs_dict['rampup_efektywnosc_billable_rok2']
            efektywnosc_sprzedaz = inputs_dict['rampup_efektywnosc_sprzedaz_rok2']
            # Założenie: R2 poświęca połowę docelowego czasu na utrzymanie
            m['godziny_na_utrzymanie_projektow'] = m['godziny_pracy_rocznie'] * \
                                                inputs_dict['konsultant_procent_czasu_utrzymanie_projektow'] * 0.5
        else: # Full
            efektywnosc_billable = 1.0
            efektywnosc_sprzedaz = 1.0
            m['godziny_na_utrzymanie_projektow'] = m['godziny_pracy_rocznie'] * \
                                                inputs_dict['konsultant_procent_czasu_utrzymanie_projektow']

        m['godziny_billable'] = m['godziny_pracy_rocznie'] * \
                                inputs_dict['konsultant_procent_czasu_billable_docelowy'] * efektywnosc_billable
        
        if typ == "Full":
             m['godziny_na_sprzedaz'] = m['godziny_pracy_rocznie'] * \
                                       inputs_dict['konsultant_procent_czasu_sprzedaz_docelowy']
        else: # Dla R1 i R2, czas na sprzedaż to reszta
            m['godziny_na_sprzedaz'] = m['godziny_pracy_rocznie'] - m['godziny_na_rozwoj_admin'] - \
                                     m['godziny_billable'] - m['godziny_na_utrzymanie_projektow']
            if m['godziny_na_sprzedaz'] < 0: m['godziny_na_sprzedaz'] = 0


        m['przychod_z_godzin_billable'] = m['godziny_billable'] * inputs_dict['konsultant_stawka_billable_godz']
        
        m['liczba_wygenerowanych_leadow'] = inputs_dict['sprzedaz_leady_rocznie_docelowo'] * efektywnosc_sprzedaz
        m['liczba_pozyskanych_kontraktow'] = m['liczba_wygenerowanych_leadow'] * inputs_dict['sprzedaz_wspolczynnik_konwersji']
        m['potencjalny_przychod_z_kontraktow'] = m['liczba_pozyskanych_kontraktow'] * inputs_dict['sprzedaz_srednia_wartosc_kontraktu']
        
        m['koszt_wynagrodzenia'] = inputs_dict['konsultant_wynagrodzenie_roczne']
        m['koszt_overheadu'] = inputs_dict['korporacyjne_overhead_roczny_na_konsultanta']
        m['calkowity_koszt_roczny_konsultanta'] = m['koszt_wynagrodzenia'] + m['koszt_overheadu']
        
        m['calkowity_przychod_potencjalny_konsultanta'] = m['przychod_z_godzin_billable'] + m['potencjalny_przychod_z_kontraktow']
        m['zysk_strata_na_konsultancie_potencjalny'] = m['calkowity_przychod_potencjalny_konsultanta'] - m['calkowity_koszt_roczny_konsultanta']
        
        metrics[typ] = m
    return metrics

def run_financial_model(inputs_dict):
    """Uruchamia 5-letnią symulację finansową."""
    
    horyzont_lat = inputs_dict['model_horyzont_analizy_lata']
    plan_rekrutacji = [
        inputs_dict['rekrutacja_rok1_nowi'], inputs_dict['rekrutacja_rok2_nowi'],
        inputs_dict['rekrutacja_rok3_nowi'], inputs_dict['rekrutacja_rok4_nowi'],
        inputs_dict['rekrutacja_rok5_nowi']
    ]

    # Oblicz metryki roczne per typ konsultanta raz
    metrics_per_consultant_type = calculate_consultant_annual_metrics(inputs_dict)

    # Inicjalizacja stanów
    konsultanci_r1_poprzedni_rok = 0
    konsultanci_r2_poprzedni_rok = 0
    konsultanci_full_poprzedni_rok = 0
    
    kontrakty_pozyskane_lacznie_poprzedni_rok = 0
    skumulowany_przeplyw_pieniezny = 0
    
    roczne_wyniki_lista = []
    calkowite_koszty_rekrutacji_do_roi = 0

    for i_rok in range(horyzont_lat):
        rok_kalendarzowy = i_rok + 1
        wyniki_biezacego_roku = {"Rok": rok_kalendarzowy}

        # --- Liczba Konsultantów ---
        nowi_w_roku = plan_rekrutacji[i_rok]
        
        przechodzacy_do_r2 = konsultanci_r1_poprzedni_rok
        przechodzacy_do_full = konsultanci_r2_poprzedni_rok
        
        biezacy_r1_eoy = nowi_w_roku
        biezacy_r2_eoy = przechodzacy_do_r2
        biezacy_full_eoy = konsultanci_full_poprzedni_rok + przechodzacy_do_full
        
        wyniki_biezacego_roku["Konsultanci R1 (koniec roku)"] = biezacy_r1_eoy
        wyniki_biezacego_roku["Konsultanci R2 (koniec roku)"] = biezacy_r2_eoy
        wyniki_biezacego_roku["Konsultanci Full (koniec roku)"] = biezacy_full_eoy
        laczna_liczba_konsultantow_eoy = biezacy_r1_eoy + biezacy_r2_eoy + biezacy_full_eoy
        wyniki_biezacego_roku["Łączna Liczba Konsultantów (koniec roku)"] = laczna_liczba_konsultantow_eoy

        # Aktualizacja stanu na następny rok
        konsultanci_r1_poprzedni_rok = biezacy_r1_eoy
        konsultanci_r2_poprzedni_rok = biezacy_r2_eoy
        konsultanci_full_poprzedni_rok = biezacy_full_eoy

        # --- Przychody ---
        przychod_billable_r1 = biezacy_r1_eoy * metrics_per_consultant_type["R1"]['przychod_z_godzin_billable']
        przychod_billable_r2 = biezacy_r2_eoy * metrics_per_consultant_type["R2"]['przychod_z_godzin_billable']
        przychod_billable_full = biezacy_full_eoy * metrics_per_consultant_type["Full"]['przychod_z_godzin_billable']
        laczny_przychod_billable = przychod_billable_r1 + przychod_billable_r2 + przychod_billable_full
        wyniki_biezacego_roku["Łączny Przychód z Godzin Billable"] = laczny_przychod_billable

        kontrakty_pozyskane_r1_w_roku = biezacy_r1_eoy * metrics_per_consultant_type["R1"]['liczba_pozyskanych_kontraktow']
        kontrakty_pozyskane_r2_w_roku = biezacy_r2_eoy * metrics_per_consultant_type["R2"]['liczba_pozyskanych_kontraktow']
        kontrakty_pozyskane_full_w_roku = biezacy_full_eoy * metrics_per_consultant_type["Full"]['liczba_pozyskanych_kontraktow']
        lacznie_kontrakty_pozyskane_biezacy_rok = kontrakty_pozyskane_r1_w_roku + kontrakty_pozyskane_r2_w_roku + kontrakty_pozyskane_full_w_roku
        wyniki_biezacego_roku["Łącznie Kontrakty Pozyskane (szt.)"] = lacznie_kontrakty_pozyskane_biezacy_rok
        
        przychod_z_kontraktow_w_roku = kontrakty_pozyskane_lacznie_poprzedni_rok * inputs_dict['sprzedaz_srednia_wartosc_kontraktu']
        wyniki_biezacego_roku["Przychód z Kontraktów (z opóźnieniem)"] = przychod_z_kontraktow_w_roku
        
        kontrakty_pozyskane_lacznie_poprzedni_rok = lacznie_kontrakty_pozyskane_biezacy_rok # Na następny rok

        calkowity_przychod_firmy = laczny_przychod_billable + przychod_z_kontraktow_w_roku
        wyniki_biezacego_roku["CAŁKOWITY PRZYCHÓD FIRMY"] = calkowity_przychod_firmy

        # --- Koszty ---
        wynagrodzenia = laczna_liczba_konsultantow_eoy * inputs_dict['konsultant_wynagrodzenie_roczne']
        wyniki_biezacego_roku["Wynagrodzenia"] = wynagrodzenia
        
        overhead = laczna_liczba_konsultantow_eoy * inputs_dict['korporacyjne_overhead_roczny_na_konsultanta']
        wyniki_biezacego_roku["Overhead"] = overhead
        
        koszty_rekrutacji = nowi_w_roku * inputs_dict['korporacyjne_koszt_rekrutacji_konsultanta']
        wyniki_biezacego_roku["Koszty Rekrutacji"] = koszty_rekrutacji
        calkowite_koszty_rekrutacji_do_roi += koszty_rekrutacji
        
        laczne_koszty_operacyjne = wynagrodzenia + overhead + koszty_rekrutacji
        wyniki_biezacego_roku["Łączne Koszty Operacyjne"] = laczne_koszty_operacyjne

        # --- Rentowność ---
        ebit = calkowity_przychod_firmy - laczne_koszty_operacyjne
        wyniki_biezacego_roku["ZYSK / STRATA OPERACYJNA (EBIT)"] = ebit
        
        marza_operacyjna = ebit / calkowity_przychod_firmy if calkowity_przychod_firmy != 0 else 0
        wyniki_biezacego_roku["MARŻA OPERACYJNA (%)"] = marza_operacyjna * 100 # Procenty

        # --- Przepływy ---
        skumulowany_przeplyw_pieniezny += ebit
        wyniki_biezacego_roku["Skumulowany przepływ pieniężny"] = skumulowany_przeplyw_pieniezny
        
        roczne_wyniki_lista.append(wyniki_biezacego_roku)

    # --- Podsumowanie ROI ---
    roi_summary = {}
    roi_summary['calkowite_koszty_rekrutacji_5lat'] = calkowite_koszty_rekrutacji_do_roi
    roi_summary['skumulowany_ebit_5lat'] = skumulowany_przeplyw_pieniezny
    
    if calkowite_koszty_rekrutacji_do_roi > 0:
        roi_summary['roi'] = skumulowany_przeplyw_pieniezny / calkowite_koszty_rekrutacji_do_roi
    else:
        roi_summary['roi'] = float('inf') if skumulowany_przeplyw_pieniezny > 0 else 0

    payback_period = "Brak zwrotu w 5 lat lub później"
    for i, rok_dane in enumerate(roczne_wyniki_lista):
        if rok_dane["Skumulowany przepływ pieniężny"] > 0:
            # Prosta wersja - rok, w którym po raz pierwszy jest dodatni
            payback_period = f"W {rok_dane['Rok']} roku"
            # TODO: Dokładniejsza interpolacja, jeśli potrzebna
            break
    roi_summary['payback_period_display'] = payback_period
    
    # Konwersja na DataFrame
    roczne_wyniki_df = pd.DataFrame(roczne_wyniki_lista)
    # Konwersja metryk konsultantów na DataFrame
    detailed_consultant_metrics_df = pd.DataFrame(metrics_per_consultant_type).T # Transpozycja dla lepszego widoku
    
    return roczne_wyniki_df, roi_summary, detailed_consultant_metrics_df

# --- Interfejs Użytkownika Streamlit ---

st.set_page_config(layout="wide", page_title="Model Biznesowy Konsulting")
st.title("📈 Model Biznesowy Firmy Konsultingowej")
st.markdown("""
Ten model symuluje finanse firmy konsultingowej w branży technologiczno-ubezpieczeniowej
na przestrzeni 5 lat. Możesz dostosować parametry wejściowe w panelu bocznym,
aby zobaczyć ich wpływ na rentowność i zwrot z inwestycji.
""")

# --- Panel Boczny z Parametrami Wejściowymi ---
st.sidebar.header("⚙️ Parametry Wejściowe")
default_inputs = get_default_inputs()
inputs = {} # Słownik do przechowywania bieżących wartości z interfejsu

# Parametry Konsultanta
st.sidebar.subheader("Konsultant")
inputs['konsultant_godziny_pracy_miesiac'] = st.sidebar.number_input(
    "Godziny pracy miesięcznie", min_value=80, max_value=200, value=default_inputs['konsultant_godziny_pracy_miesiac'], step=1)
inputs['konsultant_stawka_billable_godz'] = st.sidebar.number_input(
    "Stawka billable godzinowa (PLN)", min_value=50.0, max_value=1000.0, value=default_inputs['konsultant_stawka_billable_godz'], step=10.0, format="%.2f")
inputs['konsultant_wynagrodzenie_roczne'] = st.sidebar.number_input(
    "Wynagrodzenie roczne (PLN)", min_value=100000.0, max_value=1000000.0, value=default_inputs['konsultant_wynagrodzenie_roczne'], step=10000.0, format="%.2f")
inputs['konsultant_procent_czasu_rozwoj_admin'] = st.sidebar.slider(
    "% czasu na rozwój/admin", min_value=0.0, max_value=0.20, value=default_inputs['konsultant_procent_czasu_rozwoj_admin'], step=0.01, format="%.2f")
inputs['konsultant_procent_czasu_billable_docelowy'] = st.sidebar.slider(
    "% czasu billable (docelowy)", min_value=0.30, max_value=0.80, value=default_inputs['konsultant_procent_czasu_billable_docelowy'], step=0.01, format="%.2f")
inputs['konsultant_procent_czasu_utrzymanie_projektow'] = st.sidebar.slider(
    "% czasu na utrzymanie projektów (docelowy)", min_value=0.0, max_value=0.30, value=default_inputs['konsultant_procent_czasu_utrzymanie_projektow'], step=0.01, format="%.2f")

# Obliczany parametr - % czasu na sprzedaż
inputs['konsultant_procent_czasu_sprzedaz_docelowy'] = max(0, 1.0 - inputs['konsultant_procent_czasu_rozwoj_admin'] - \
                                                       inputs['konsultant_procent_czasu_billable_docelowy'] - \
                                                       inputs['konsultant_procent_czasu_utrzymanie_projektow'])
st.sidebar.markdown(f"_% czasu na sprzedaż (obliczone): {inputs['konsultant_procent_czasu_sprzedaz_docelowy']:.2%}_")


# Parametry Ramp-up
st.sidebar.subheader("Ramp-up")
inputs['rampup_efektywnosc_billable_rok1'] = st.sidebar.slider(
    "Efektywność Billable - Rok 1", min_value=0.0, max_value=1.0, value=default_inputs['rampup_efektywnosc_billable_rok1'], step=0.01, format="%.2f")
inputs['rampup_efektywnosc_billable_rok2'] = st.sidebar.slider(
    "Efektywność Billable - Rok 2", min_value=0.0, max_value=1.0, value=default_inputs['rampup_efektywnosc_billable_rok2'], step=0.01, format="%.2f")
inputs['rampup_efektywnosc_sprzedaz_rok1'] = st.sidebar.slider(
    "Efektywność Sprzedażowa - Rok 1", min_value=0.0, max_value=1.0, value=default_inputs['rampup_efektywnosc_sprzedaz_rok1'], step=0.01, format="%.2f")
inputs['rampup_efektywnosc_sprzedaz_rok2'] = st.sidebar.slider(
    "Efektywność Sprzedażowa - Rok 2", min_value=0.0, max_value=1.0, value=default_inputs['rampup_efektywnosc_sprzedaz_rok2'], step=0.01, format="%.2f")

# Parametry Sprzedażowe
st.sidebar.subheader("Sprzedaż")
inputs['sprzedaz_leady_rocznie_docelowo'] = st.sidebar.number_input(
    "Leady kwalifikowane rocznie/konsultant (docelowo)", min_value=1, max_value=20, value=default_inputs['sprzedaz_leady_rocznie_docelowo'], step=1)
inputs['sprzedaz_srednia_wartosc_kontraktu'] = st.sidebar.number_input(
    "Średnia wartość kontraktu (PLN)", min_value=100000.0, max_value=10000000.0, value=default_inputs['sprzedaz_srednia_wartosc_kontraktu'], step=100000.0, format="%.2f")
inputs['sprzedaz_wspolczynnik_konwersji'] = st.sidebar.slider(
    "Współczynnik konwersji (lead -> kontrakt)", min_value=0.0, max_value=1.0, value=default_inputs['sprzedaz_wspolczynnik_konwersji'], step=0.01, format="%.2f")

# Parametry Korporacyjne
st.sidebar.subheader("Korporacyjne")
inputs['korporacyjne_overhead_roczny_na_konsultanta'] = st.sidebar.number_input(
    "Overhead roczny na konsultanta (PLN)", min_value=0.0, max_value=500000.0, value=default_inputs['korporacyjne_overhead_roczny_na_konsultanta'], step=10000.0, format="%.2f")
inputs['korporacyjne_koszt_rekrutacji_konsultanta'] = st.sidebar.number_input(
    "Koszt rekrutacji konsultanta (PLN)", min_value=0.0, max_value=300000.0, value=default_inputs['korporacyjne_koszt_rekrutacji_konsultanta'], step=10000.0, format="%.2f")

# Plan Rekrutacji
st.sidebar.subheader("Plan Rekrutacji (nowi konsultanci)")
inputs['rekrutacja_rok1_nowi'] = st.sidebar.number_input("Rok 1", min_value=0, max_value=10, value=default_inputs['rekrutacja_rok1_nowi'], step=1)
inputs['rekrutacja_rok2_nowi'] = st.sidebar.number_input("Rok 2", min_value=0, max_value=10, value=default_inputs['rekrutacja_rok2_nowi'], step=1)
inputs['rekrutacja_rok3_nowi'] = st.sidebar.number_input("Rok 3", min_value=0, max_value=10, value=default_inputs['rekrutacja_rok3_nowi'], step=1)
inputs['rekrutacja_rok4_nowi'] = st.sidebar.number_input("Rok 4", min_value=0, max_value=10, value=default_inputs['rekrutacja_rok4_nowi'], step=1)
inputs['rekrutacja_rok5_nowi'] = st.sidebar.number_input("Rok 5", min_value=0, max_value=10, value=default_inputs['rekrutacja_rok5_nowi'], step=1)

# Ukryte, ale potrzebne
inputs['model_horyzont_analizy_lata'] = default_inputs['model_horyzont_analizy_lata']


# --- Główny Panel z Wynikami ---
if st.sidebar.button("🚀 Uruchom Model", type="primary", use_container_width=True):
    with st.spinner("Przetwarzanie modelu..."):
        yearly_results_df, roi_summary, detailed_consultant_metrics_df = run_financial_model(inputs)

        st.subheader("📊 Wyniki Modelu Finansowego (Roczne)")
        
        # Formatowanie DataFrame dla czytelności
        formatted_df = yearly_results_df.copy()
        currency_columns = ["Łączny Przychód z Godzin Billable", "Przychód z Kontraktów (z opóźnieniem)",
                            "CAŁKOWITY PRZYCHÓD FIRMY", "Wynagrodzenia", "Overhead", "Koszty Rekrutacji",
                            "Łączne Koszty Operacyjne", "ZYSK / STRATA OPERACYJNA (EBIT)", "Skumulowany przepływ pieniężny"]
        for col in currency_columns:
            if col in formatted_df.columns:
                 formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:,.0f} PLN")
        
        if "MARŻA OPERACYJNA (%)" in formatted_df.columns:
            formatted_df["MARŻA OPERACYJNA (%)"] = formatted_df["MARŻA OPERACYJNA (%)"].apply(lambda x: f"{x:.2f}%")

        # Zmiana nazw kolumn dla lepszej prezentacji
        column_rename_map = {
            "Konsultanci R1 (koniec roku)": "Kons. R1",
            "Konsultanci R2 (koniec roku)": "Kons. R2",
            "Konsultanci Full (koniec roku)": "Kons. Full",
            "Łączna Liczba Konsultantów (koniec roku)": "∑ Kons.",
            "Łącznie Kontrakty Pozyskane (szt.)": "Kontrakty (szt.)"
        }
        display_df = formatted_df.rename(columns=column_rename_map)
        st.dataframe(display_df, use_container_width=True)

        st.subheader("🏆 Kluczowe Wskaźniki (po 5 latach)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Skumulowany EBIT", f"{roi_summary.get('skumulowany_ebit_5lat', 0):,.0f} PLN")
        col2.metric("Proste ROI", f"{roi_summary.get('roi', 0):.2%}")
        col3.metric("Okres Zwrotu", f"{roi_summary.get('payback_period_display', 'N/A')}")

        st.subheader("📈 Wykresy")
        if not yearly_results_df.empty:
            # Wykres EBIT i Skumulowanego Przepływu
            chart_data_ebit = yearly_results_df[['Rok', 'ZYSK / STRATA OPERACYJNA (EBIT)', 'Skumulowany przepływ pieniężny']].set_index('Rok')
            st.line_chart(chart_data_ebit)

            # Wykres Struktury Przychodów
            revenue_chart_data = yearly_results_df[['Rok', 'Łączny Przychód z Godzin Billable', 'Przychód z Kontraktów (z opóźnieniem)']].set_index('Rok')
            st.bar_chart(revenue_chart_data)
            
            # Wykres Liczby Konsultantów
            consultant_chart_data = yearly_results_df[['Rok', 'Konsultanci R1 (koniec roku)', 'Konsultanci R2 (koniec roku)', 'Konsultanci Full (koniec roku)']].set_index('Rok')
            st.area_chart(consultant_chart_data)


        st.subheader("📄 Szczegółowe Kalkulacje Roczne dla Typów Konsultantów")
        # Formatowanie tabeli metryk konsultantów
        formatted_metrics_df = detailed_consultant_metrics_df.copy()
        metrics_currency_cols = ['przychod_z_godzin_billable', 'potencjalny_przychod_z_kontraktow', 
                                 'koszt_wynagrodzenia', 'koszt_overheadu', 'calkowity_koszt_roczny_konsultanta',
                                 'calkowity_przychod_potencjalny_konsultanta', 'zysk_strata_na_konsultancie_potencjalny']
        metrics_hours_cols = ['godziny_pracy_rocznie', 'godziny_na_rozwoj_admin', 'godziny_billable', 
                              'godziny_na_utrzymanie_projektow', 'godziny_na_sprzedaz']
        
        for col in metrics_currency_cols:
            if col in formatted_metrics_df.columns:
                formatted_metrics_df[col] = formatted_metrics_df[col].apply(lambda x: f"{x:,.0f} PLN")
        for col in metrics_hours_cols:
            if col in formatted_metrics_df.columns:
                 formatted_metrics_df[col] = formatted_metrics_df[col].apply(lambda x: f"{x:,.0f} godz.")
        
        if 'liczba_wygenerowanych_leadow' in formatted_metrics_df.columns:
            formatted_metrics_df['liczba_wygenerowanych_leadow'] = formatted_metrics_df['liczba_wygenerowanych_leadow'].apply(lambda x: f"{x:.1f} szt.")
        if 'liczba_pozyskanych_kontraktow' in formatted_metrics_df.columns:
            formatted_metrics_df['liczba_pozyskanych_kontraktow'] = formatted_metrics_df['liczba_pozyskanych_kontraktow'].apply(lambda x: f"{x:.1f} szt.")

        st.dataframe(formatted_metrics_df, use_container_width=True)


else:
    st.info("Dostosuj parametry w panelu bocznym i kliknij '🚀 Uruchom Model', aby zobaczyć wyniki.")

# --- Instrukcja Użycia ---
with st.expander("📜 Instrukcja Uruchomienia i Użycia"):
    st.markdown("""
 
    **Jak używać modelu:**

    *   **Panel Boczny:** Po lewej stronie znajduje się panel z parametrami wejściowymi. Są one podzielone na kategorie (Konsultant, Ramp-up, Sprzedaż, itd.).
    *   **Modyfikacja Parametrów:** Możesz zmieniać wartości liczbowe, procentowe (za pomocą suwaków) oraz plany rekrutacji. Zwróć uwagę, że "% czasu na sprzedaż" jest obliczany automatycznie na podstawie innych alokacji czasu.
    *   **Uruchomienie Modelu:** Po dostosowaniu parametrów, kliknij duży przycisk "🚀 Uruchom Model" na dole panelu bocznego.
    *   **Wyniki:** W głównej części aplikacji pojawią się:
        *   Tabela z rocznymi wynikami finansowymi firmy.
        *   Kluczowe wskaźniki ROI i okres zwrotu.
        *   Wykresy ilustrujące dynamikę EBIT, skumulowanych przepływów, struktury przychodów oraz liczby konsultantów.
        *   Tabela ze szczegółowymi rocznymi kalkulacjami dla typów konsultantów (R1, R2, Full).
    *   **Eksperymentowanie:** Zachęcam do eksperymentowania z różnymi wartościami parametrów, aby zrozumieć ich wpływ na rentowność i rozwój firmy.

    """)
