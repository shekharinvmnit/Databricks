import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Updated path to match the file currently in your GitHub repository
DATA_PATH = os.path.join(os.path.dirname(__file__), 'TeamRankApp.xlsx - Sheet1.csv')

# Load teams from CSV
@st.cache_data
def load_teams():
    if not os.path.exists(DATA_PATH):
        return []
    try:
        df = pd.read_csv(DATA_PATH)
        names = df.iloc[:, 0].dropna().astype(str).tolist()
        # Remove header if present
        if names and names[0].strip().lower() in ['name', 'team', 'team name']:
            names = names[1:]
        teams = [n.strip() for n in names if n.strip()]
        return teams
    except Exception as e:
        st.error(f"Error loading teams: {e}")
        return []

# Load the full DataFrame
@st.cache_data
def load_df():
    if not os.path.exists(DATA_PATH):
        st.error(f"File not found: {DATA_PATH}")
        return pd.DataFrame()
    return pd.read_csv(DATA_PATH)

# Save DataFrame to CSV
def save_df(df):
    # Note: On Streamlit Cloud, this save is temporary and will reset on reboot
    df.to_csv(DATA_PATH, index=False)

# Sidebar navigation
st.sidebar.title('Navigation')
page = st.sidebar.radio('Go to', ['Update Points', 'View Points Table', 'Delete Date Range'])

st.title('Team Ranking Web App')

if page == 'Update Points':
    teams = load_teams()
    if not teams:
        st.warning('No teams found. Please check your CSV file.')
    else:
        with st.form("update_form"):
            selected_date = st.date_input("Select Date", datetime.now())
            date_str = selected_date.strftime('%Y-%m-%d')
            
            updates = {}
            for team in teams:
                updates[team] = st.number_input(f"Points for {team}", value=0)
            
            submit = st.form_submit_button("Update Points")
            
            if submit:
                df = load_df()
                if date_str not in df.columns:
                    df[date_str] = 0
                
                for team, points in updates.items():
                    df.loc[df.iloc[:, 0] == team, date_str] = points
                
                # Update Balance (Sum of all date columns)
                date_cols = [c for c in df.columns if c not in ['Name', 'Balance']]
                df['Balance'] = df[date_cols].sum(axis=1)
                
                save_df(df)
                st.cache_data.clear()
                st.success(f"Points updated for {date_str}!")

elif page == 'View Points Table':
    df = load_df()
    if not df.empty:
        st.dataframe(df)
    else:
        st.info("No data available to display.")

elif page == 'Delete Date Range':
    df = load_df()
    if not df.empty:
        date_cols = [c for c in df.columns if c not in ['Name', 'Balance']]
        
        # Date parsing logic for filtering
        import re
        import dateutil.parser
        def parse_date_col(col):
            try:
                base = re.match(r'(\d{4}-\d{2}-\d{2})', str(col))
                if base:
                    return datetime.strptime(base.group(1), '%Y-%m-%d').date()
                return dateutil.parser.parse(str(col)[:10]).date()
            except:
                return None

        parsed_dates = [(c, parse_date_col(c)) for c in date_cols]
        valid_dates = [d for c, d in parsed_dates if d is not None]
        
        if valid_dates:
            min_date, max_date = min(valid_dates), max(valid_dates)
            start_date = st.date_input('Start Date', value=min_date)
            end_date = st.date_input('End Date', value=max_date)
            
            if st.button('Delete Data in Range'):
                cols_to_keep = ['Name', 'Balance']
                for col, dt in parsed_dates:
                    if dt is None or not (start_date <= dt <= end_date):
                        cols_to_keep.append(col)
                
                new_df = df[cols_to_keep]
                # Recalculate Balance
                rem_date_cols = [c for c in new_df.columns if c not in ['Name', 'Balance']]
                new_df['Balance'] = new_df[rem_date_cols].sum(axis=1)
                
                save_df(new_df)
                st.cache_data.clear()
                st.success("Selected range deleted.")