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
        n_quarter_h = self.number_of_quarter_h(start_day, start_t, end_day, end_t)
        self.zeit = [i for i in range(n_quarter_h)]
        print(self.zeit)
        self.mhkwa = np.zeros(n_quarter_h)
        self.mhkwn = np.zeros(n_quarter_h)
        self.hwea = np.zeros(n_quarter_h)
        self.hwen = np.zeros(n_quarter_h)
        self.speicher = np.zeros(n_quarter_h)
        self.initial_speicher = speicher
        self.laden = np.zeros(n_quarter_h)
        self.create_initial_df(start_day, start_t, n_quarter_h)
        self.excel_path = excel_path
        self.excel_name = excel_name
        self.load_prognose()
        self.create_prognose_df()
    
    def number_of_quarter_h(self, start_date, start_t, end_date, end_t):
        start = datetime.datetime.combine(start_date, start_t)
        end = datetime.datetime.combine(end_date, end_t)
        n_quarter_h = (end - start).total_seconds() /60 / 15
        print(n_quarter_h)
        return int(n_quarter_h)
        
    def create_initial_df(self, start_day, start_t, n_quarter_h):
        self.initial_df = pd.DataFrame(np.stack([self.zeit, self.mhkwa, self.mhkwn, self.hwea, self.hwen, self.laden, self.speicher],axis=-1), columns=['zeit', 'mhkwa', 'mhkwn', 'hwea', 'hwen', 'laden', 'speicher'])  
        date = self.create_time_index(start_date=start_day, start_t=start_t, n_quarter_h=n_quarter_h)
        self.initial_df['zeit'] = date
        self.initial_df = self.initial_df.set_index('zeit')
    
    def create_time_index(self, start_date=datetime.date.today(), start_t='00:00:00', n_quarter_h=96):
        time = datetime.datetime.combine(start_date, start_t)
        date = pd.to_datetime(time)
        date = date + pd.to_timedelta(np.arange(stop=n_quarter_h*15, step=15), 'min')
        return date
        
    def calc_speicher(self, df):
        df.loc[:,'laden'] = df['prognose'] - df['mhkwa'] - df['mhkwn'] - df['hwea'] - df['hwen']
        df.loc[:,'speicher'] = - df['laden']/4.0
        df.loc[:,'speicher'] = df['speicher'].expanding(1).sum() + self.initial_speicher
        return df
        
    def load_prognose(self):
        self.prognose_excel = pd.read_csv(os.path.join(self.excel_path, self.excel_name), sep=';', header=7, index_col=0, encoding='ISO-8859-1', decimal=',').rename(columns={'Value': 'prognose', 'Value.1': 'strom'})['prognose'].dropna()
        self.prognose_excel.index = pd.to_datetime(self.prognose_excel.index, dayfirst=True)
        # for date in start, end .date unique load prognose file, add to df
    
    def create_prognose_df(self):
        self.prognose_df = self.initial_df.join(self.prognose_excel, how='left',lsuffix='', rsuffix='_y').fillna(0).dropna()
        print(self.prognose_excel, self.initial_df, self.prognose_df)
        self.prognose_df.drop(self.prognose_df.filter(regex='_y$').columns, axis=1, inplace=True)
        self.prognose_df = self.calc_speicher(self.prognose_df)
        if self.prognose_df.empty:
            self.prognose_df = self.initial_df
            self.prognose_df['prognose'] = np.zeros(len(self.prognose_df))
            self.prognose_df = self.calc_speicher(self.prognose_df)
            st.write('Prognose konnte nicht geladen werden')

    def select_time(self, start, end):
        try:
            df = self.prognose_df[start:end]
        except:
            st.write('used initial df')
            df = self.initial_df[start:end]
        return df

def save_edits():
    st.session_state.df_temp = st.session_state.df_temp_edited.copy()
    
def get_input_current_df(current_df):
    st.session_state.df_temp_edited = st.data_editor(current_df, column_config={'laden':None, 'speicher':None}, column_order=('prognose', 'mhkwa', 'mhkwn', 'hwea', 'hwen'))

def newest_file(file_path, file_name, pattern):
    
    files = []
    for file in os.listdir(file_path):
        if os.path.isfile(os.path.join(file_path,file)):
            if re.match(pattern, file) is not None:
                print('found', file)
                print(re.match(pattern, file).group(0))
                files.append(os.path.join(file_path, re.match(pattern, file).group(0)))
    
    time = 0
    for file in files:
        path = os.path.join(file_path, file)
        modified_time = os.stat(path).st_mtime
        if time < modified_time:
            time = modified_time
            newest_file = os.path.basename(file)
   
    return newest_file

def date_parser(datum):
    return str(datum).replace('-', '')

def main():
    print('hi')
    
    datum = st.date_input('Datum', value=(datetime.date.today(),datetime.date.today() + datetime.timedelta(days=1)), key='start_date')
    t_start = st.time_input('Start', value=datetime.time(0,15,0), key='start_time')
    t_end = st.time_input('Ende', value=datetime.time(23,45,0), key='end_time')
    start = datetime.datetime.combine(datum[0], t_start)
    end = datetime.datetime.combine(datum[1], t_end)
    
    speicher_initial = st.number_input('Initialer Speicherstand', min_value=0, max_value=400, value='min')
    
    #get_all_dates()
    date_string = date_parser(datum[0])
    file_name = date_string + '_Wärme-HS-Last.*.csv'
    print('File name', file_name)
    file_path = r'Z:\BelVis\Export\Ist_Werte'
    #file_name = '.*_ID_Tagesfahrplan_v12.4.xlsm'
    #file_path = os.path.join(os.path.expanduser('~'),'Desktop', 'waerme')
    file_name_pattern = re.compile(file_name)
    
    if 'file_name' not in  st.session_state:
        st.session_state.file_name = file_name
        
    st.session_state.file_name = newest_file(file_path, st.session_state.file_name, file_name_pattern)
    print(st.session_state.file_name)
    
    test = waerme_prog(start_day=datum[0], start_t=t_start, end_day=datum[1], end_t=t_end, speicher=speicher_initial, excel_path=file_path, excel_name=st.session_state.file_name)
    test.calc_speicher(test.prognose_df)
    
    col1, col2 = st.columns(2)
    
    current_df = test.select_time(start, end)
    
    if 'df_temp' not in st.session_state:
        st.session_state.df_temp = current_df.copy()
        st.session_state.df_temp_edited = st.session_state.df_temp.copy()
    
    with col1:
        col11,  col12, col13 = st.columns(3)
        with col11:
            if st.button('Reset Eingabe', on_click=save_edits):
                for cols in st.session_state.df_temp.columns:
                    st.session_state.df_temp[cols].values[:] = 0
        
        with col12:
            if st.button('Lade Prognose', on_click=save_edits):
                test.load_prognose()
                test.create_prognose_df()
                prognose = test.select_time(start, end)['prognose']
                st.session_state.df_temp['prognose'] = prognose.copy()
        
        with col13:
            if st.button('Lade neue Zeiten', on_click=save_edits):
                st.session_state.df_temp = test.select_time(start, end)
                merged_df_temp = st.session_state.df_temp.join(st.session_state.df_temp_edited, how='left', lsuffix='', rsuffix='_y')
                index = merged_df_temp.dropna().index
                st.session_state.df_temp.loc[index,:] = st.session_state.df_temp_edited.loc[index,:]
                
        get_input_current_df(st.session_state.df_temp)
    
    with col2:
        st.write('Ergebnis Speicherstand')
        st.dataframe(test.calc_speicher(st.session_state.df_temp_edited))
    
if __name__ == "__main__":
    main()