import sys
import os
import re
import numpy as np
import pandas as pd
import datetime
import streamlit as st
st.set_page_config(layout='wide')

class waerme_prog:
    def __init__(self, speicher=0, excel_path=os.path.join(os.path.expanduser('~'),'Desktop', 'waerme'), excel_name='2024_05_17_ID_Tagesfahrplan_v12.4.xlsm', start_day=datetime.date.today(), start_t=None, end_day=datetime.date.today(), end_t=None):
        # Anzahl der Viertelstunden berechnet aus Start und End-Zeit für Initialisierung der Prognosetabelle
        n_quarter_h = self.number_of_quarter_h(start_day, start_t, end_day, end_t)
        # Initialisierung der Zeitreihen für Prognosetabelle
        self.zeit = [i for i in range(n_quarter_h)]
        self.mhkwa = np.zeros(n_quarter_h)
        self.mhkwn = np.zeros(n_quarter_h)
        self.hwea = np.zeros(n_quarter_h)
        self.hwen = np.zeros(n_quarter_h)
        self.speicher = np.zeros(n_quarter_h)
        self.laden = np.zeros(n_quarter_h)
        # Initialer Speicherstand
        self.initial_speicher = speicher
        #Erzeuge initiale Prognosetabelle
        self.create_initial_df(start_day, start_t, n_quarter_h)
        #Setze Pfad und Name der Quelldatei für Prognose
        self.excel_path = excel_path
        self.excel_name = excel_name
        #Lade Prognose aus Quelldatei
        self.load_prognose()
        #Erzeuge die Prognosetabelle mit den korrekten Zeiten
        self.create_prognose_df()
    
    def number_of_quarter_h(self, start_date, start_t, end_date, end_t):
    """
    Berechnet Anzahl der Viertelsunden aus Start- und Endzeit
    ---
    start_date: Startdatum datetime.date
    start_t: Startzeit datetime.time
    end_date: Enddatum datetime.date
    end_time: Endzeit datetime.time
    """
        start = datetime.datetime.combine(start_date, start_t)
        end = datetime.datetime.combine(end_date, end_t)
        # Beerechne Anzahl 1/4h aus Zeitdifferenz in sec
        n_quarter_h = (end - start).total_seconds() /60 / 15
        print(n_quarter_h)
        return int(n_quarter_h)
        
    def create_initial_df(self, start_day, start_t, n_quarter_h):
    """
    Erzeuge initiale Tabelle über alle Viertel Stunden mit Null-Werten
    ---
    start_day: Startdatum datetime.date
    start_t: Startzeit datetime.time
    n_quarter_h: Anzahl Viertelstunden int
    """
        #Erzeuge pandas df mit initialen Zeitreihen für n_quarter_h Viertelstunden
        self.initial_df = pd.DataFrame(np.stack([self.zeit, self.mhkwa, self.mhkwn, self.hwea, self.hwen, self.laden, self.speicher],axis=-1), columns=['zeit', 'mhkwa', 'mhkwn', 'hwea', 'hwen', 'laden', 'speicher'])  
        #Erzeuge den Zeitreihenindex
        date = self.create_time_index(start_date=start_day, start_t=start_t, n_quarter_h=n_quarter_h)
        self.initial_df['zeit'] = date
        self.initial_df = self.initial_df.set_index('zeit')
    
    def create_time_index(self, start_date=datetime.date.today(), start_t='00:00:00', n_quarter_h=96):
    """
    Erzeuge die Zeitreihe für den Zeitreihenindex aus Startdatum, Startzeit und Anzahl Viertelstunden
    ---
    start_day: Startdatum datetime.date
    start_t: Startzeit datetime.time
    n_quarter_h: Anzahl Viertelstunden int
    """
        time = datetime.datetime.combine(start_date, start_t)
        date = pd.to_datetime(time)
        #Zähle in Viertelstundenschritten hoch und erzeuge timestamps
        date = date + pd.to_timedelta(np.arange(stop=n_quarter_h*15, step=15), 'min')
        return date
        
    def calc_speicher(self, df):
    """
    Errechnet den Soeicherstand und die Laderaten anhand der Prognose und der Spalten der Anlagenleistung
    ---
    df: Prognosetabelle pandas dataframe
    """
        # laden = Stadtlast - Erzeugung -> positiv/entladen, negativ/laden
        df.loc[:,'laden'] = df['prognose'] - df['mhkwa'] - df['mhkwn'] - df['hwea'] - df['hwen']
        #setze Laderate pro Viertelstunde
        df.loc[:,'speicher'] = - df['laden']/4.0
        #Berechner Speicherstand durch Addition vorherige Stunde Speicherstand mit Laderate + initialer Speicherstand
        df.loc[:,'speicher'] = df['speicher'].expanding(1).sum() + self.initial_speicher
        return df
        
    def load_prognose(self):
    """
    Lade die Prognose aus der Datenquelle in einen pandas df
    ---
    benutze excel_path und excel_name um df prognose excel zu erzeugen
    """
        self.prognose_excel = pd.read_csv(os.path.join(self.excel_path, self.excel_name), sep=';', header=7, index_col=0, encoding='ISO-8859-1', decimal=',').rename(columns={'Value': 'prognose', 'Value.1': 'strom'})['prognose'].dropna()
        self.prognose_excel.index = pd.to_datetime(self.prognose_excel.index, dayfirst=True)
    
    def create_prognose_df(self):
    """
    Erzeuge Tabelle mit Prognose
    """
        #join Initiale Tabelle mit geladener Prognose an Hand des Zeitindexes
        self.prognose_df = self.initial_df.join(self.prognose_excel, how='left',lsuffix='', rsuffix='_y').fillna(0).dropna()
        #Verwerfe doppelte Spalten
        self.prognose_df.drop(self.prognose_df.filter(regex='_y$').columns, axis=1, inplace=True)
        #Errechne neuen Speicherstand
        self.prognose_df = self.calc_speicher(self.prognose_df)
        #Falls keine Zeiten übereinstimmen oder Fehler auftritt ist prognose_df leer
        #dann initialisiere mit 0 und gib Warnung aus
        if self.prognose_df.empty:
            self.prognose_df = self.initial_df
            self.prognose_df['prognose'] = np.zeros(len(self.prognose_df))
            self.prognose_df = self.calc_speicher(self.prognose_df)
            st.write('Prognose konnte nicht geladen werden')

    def select_time(self, start, end):
    """
    Wähle ein Zeitfenster in der Prognosetabelle und gib diese gefilterte Tabelle zurück
    ---
    start: Startzeitpunkt (Datum und Uhrzeit) datetime.date
    end: Endzeitpunkt (Datum und Uhrzeit) datetime.date
    """
        try:
            df = self.prognose_df[start:end]
        except:
            st.write('used initial df')
            df = self.initial_df[start:end]
        return df

def save_edits():
"""
speichere Änderungen an der Tabelle im streamlit session state für nächsten Durchlauf des Programms
"""
    st.session_state.df_temp = st.session_state.df_temp_edited.copy()
    
def get_input_current_df(current_df):
"""
Hole neuen Input ab und ppeichere den aktuellen neuen Input in temporärer Variable
---
current_df: aktuelle Tabelle, die verändert wird pandas dataframe
"""
    st.session_state.df_temp_edited = st.data_editor(current_df, column_config={'laden':None, 'speicher':None}, column_order=('prognose', 'mhkwa', 'mhkwn', 'hwea', 'hwen'))

def newest_file(file_path, pattern):
 """
 Suche Name der neusten (Bearbeitungszeit) Datei, die pattern im Dateinamen beeinhaltet
 ---
 file_path: Pfad in der Quelldatei liegt string
 pattern: Suchpattern für Dateiname regular expression string
 """
    files = []
    #Suche dateien im Dateipfad
    for file in os.listdir(file_path):
        # wenn es sich um eine Datei handellt
        if os.path.isfile(os.path.join(file_path,file)):
            # wenn es eine Übereinstimmung zwischen pattern und Dateiname gibt
            if re.match(pattern, file) is not None:
                #füge Dateiname zur Liste der gefundenen Übereinstimmungen hinzu
                files.append(os.path.join(file_path, re.match(pattern, file).group(0)))
    
    time = 0
    #für alle Übereinstimmungen
    for file in files:
        path = os.path.join(file_path, file)
        #Zeit seit der letzten Modifikation
        modified_time = os.stat(path).st_mtime
        #wenn Zeit seit der letzten Modifikation kleiner als aktuell neuste Modifikationszeit -> setze aktuellste Datei
        if time < modified_time:
            time = modified_time
            newest_file = os.path.basename(file)
   
    return newest_file

def date_parser(datum):
"""
Ersetze - in Zeitstring der Quelldatei um erfolgreiches Einlesen zu gewährleisten
"""
    return str(datum).replace('-', '')

def main():
    print('Start')
    
    #Auswahl der Startzeit/Endzeit, Datum und Uhrzeit
    datum = st.date_input('Datum', value=(datetime.date.today(),datetime.date.today() + datetime.timedelta(days=1)), key='start_date')
    t_start = st.time_input('Start', value=datetime.time(0,15,0), key='start_time')
    t_end = st.time_input('Ende', value=datetime.time(23,45,0), key='end_time')
    start = datetime.datetime.combine(datum[0], t_start)
    end = datetime.datetime.combine(datum[1], t_end)
    
    #eingabe initialer Speicherstand
    speicher_initial = st.number_input('Initialer Speicherstand', min_value=0, max_value=400, value='min')
    
    #Suchpattern für Wärmelast-Quelldatei erzeugen
    date_string = date_parser(datum[0])
    file_name = date_string + '_Wärme-HS-Last.*.csv'
    print('File name', file_name)
    #Dateipfad der Quelldatei
    file_path = r'Z:\BelVis\Export\Ist_Werte'
    #erzeuge regular expression als Suchpattern
    file_name_pattern = re.compile(file_name)
    
    #Erzeuge Programmlauf-übergreifende Variable für Name der neusten Quelldatei Prognose  
    if 'file_name' not in  st.session_state:
        st.session_state.file_name = file_name
        
    #Suche und speichere Name der neusten Quelldate Prognose
    st.session_state.file_name = newest_file(file_path, file_name_pattern)
    
    #lade waerme_prog class und initialisiere
    prog = waerme_prog(start_day=datum[0], start_t=t_start, end_day=datum[1], end_t=t_end, speicher=speicher_initial, excel_path=file_path, excel_name=st.session_state.file_name)
    prog.calc_speicher(prog.prognose_df)
    
    #Spalten für streamlit web gui
    col1, col2 = st.columns(2)
    
    #initialisiere aktuelle Tabelle
    current_df = prog.select_time(start, end)
    
    #erzeuge programmlauf-übergreifende Variable für aktuelle und temporäre Prognosse Tabellen
    if 'df_temp' not in st.session_state:
        st.session_state.df_temp = current_df.copy()
        st.session_state.df_temp_edited = st.session_state.df_temp.copy()
    
    with col1:
        col11,  col12, col13 = st.columns(3)
        with col11:
            #Reset button, setze gesamte aktuelle Tabelle auf 0
            if st.button('Reset Eingabe', on_click=save_edits):
                for cols in st.session_state.df_temp.columns:
                    st.session_state.df_temp[cols].values[:] = 0
        
        with col12:
            #Lade Prognose Button, lade Prognose erneut, Achtung: resettet aktuelle Eingabe der Fahrpläne auf 0
            if st.button('Lade Prognose', on_click=save_edits):
                prog.load_prognose()
                prog.create_prognose_df()
                prognose = prog.select_time(start, end)['prognose']
                st.session_state.df_temp['prognose'] = prognose.copy()
        
        with col13:
            # Lade neue Zeiten Button, aktualisiere aktuelle ptognose Tabelle auf eingestellten Zeitrahmen
            if st.button('Lade neue Zeiten', on_click=save_edits):
                st.session_state.df_temp = prog.select_time(start, end)
                merged_df_temp = st.session_state.df_temp.join(st.session_state.df_temp_edited, how='left', lsuffix='', rsuffix='_y')
                index = merged_df_temp.dropna().index
                st.session_state.df_temp.loc[index,:] = st.session_state.df_temp_edited.loc[index,:]
        
        #Aufnahme der aktuellen eingaben aus dem Web-gui
        get_input_current_df(st.session_state.df_temp)
    
    with col2:
        #Erzeuge Ergebnis-Tabelle
        st.write('Ergebnis Speicherstand')
        st.dataframe(prog.calc_speicher(st.session_state.df_temp_edited))
    
if __name__ == "__main__":
    main()