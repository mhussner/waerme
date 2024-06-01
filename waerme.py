import sys
import os
import numpy as np
import pandas as pd
import datetime
import streamlit as st
st.set_page_config(layout='wide')

class waerme_prog:
    def __init__(self, speicher=0, excel_path=os.path.join(os.path.expanduser('~'),'Desktop', 'waerme'), excel_name='2024_05_17_ID_Tagesfahrplan_v12.4.xlsm', timestamp=datetime.date.today()):
        self.timestamp = timestamp
        self.zeit = [i for i in range(96)]
        self.mhkwa = np.zeros(96)
        self.mhkwn = np.zeros(96)
        self.hwea = np.zeros(96)
        self.hwen = np.zeros(96)
        self.speicher = np.zeros(96)
        self.initial_speicher = speicher
        self.laden = np.zeros(96)
        self.create_initial_df()
        self.excel_path = excel_path
        self.excel_name = excel_name
        self.load_prognose()
        self.create_prognose_df()
    
    def create_initial_df(self):
        self.initial_df = pd.DataFrame(np.stack([self.zeit, self.mhkwa, self.mhkwn, self.hwea, self.hwen, self.laden, self.speicher],axis=-1), columns=['zeit', 'mhkwa', 'mhkwn', 'hwea', 'hwen', 'laden', 'speicher'])  
        date = self.create_time_index(time=self.timestamp)
        self.initial_df['zeit'] = date
        self.initial_df = self.initial_df.set_index('zeit')
    
    def create_time_index(self, time='1st january of 0', start=None, stop=None):
        date = pd.to_datetime(time) + pd.to_timedelta(15, 'min')
        date = date + pd.to_timedelta(np.arange(stop=96*15, step=15), 'min')
        return date
        
    def calc_speicher(self, df):
        df.loc[:,'laden'] = df['prognose'] - df['mhkwa'] - df['mhkwn'] - df['hwea'] - df['hwen']
        df.loc[:,'speicher'] = - df['laden']/4.0
        df.loc[:,'speicher'] = df['speicher'].expanding(1).sum() + self.initial_speicher
        return df
        
    def load_prognose(self):
        self.prognose_excel = pd.read_excel(os.path.join(self.excel_path, self.excel_name), sheet_name='ID', header=11, index_col=17).rename(columns={'Unnamed: 18': 'prognose'})['prognose'].dropna()
    
    def create_prognose_df(self):
        self.prognose_df = self.initial_df.join(self.prognose_excel, how='inner',lsuffix='', rsuffix='_y').dropna()
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
    st.session_state.df_temp_edited = st.data_editor(current_df, column_config={'laden':None, 'speicher':None})

def main():
    print('hi')
    
    datum = st.date_input('Datum', value=(datetime.date.today(),datetime.date.today() + datetime.timedelta(days=1)), key='start_date')
    t_start = st.time_input('Start', value=None, key='start_time')
    t_end = st.time_input('Ende', value=None, key='end_time')
    start = datetime.datetime.combine(datum[0], t_start)
    end = datetime.datetime.combine(datum[1], t_end)
    
    speicher_initial = st.number_input('Initialer Speicherstand', min_value=0, max_value=400, value='min')
    
    test = waerme_prog(speicher=speicher_initial, timestamp=datum[0])
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