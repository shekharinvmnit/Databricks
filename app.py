
import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Path to the Excel file
EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'TeamRankApp.xlsx')

# Load teams from Excel
@st.cache_data
def load_teams():
    df = pd.read_excel(EXCEL_PATH, engine='openpyxl')
    names = df.iloc[:, 0].dropna().astype(str).tolist()
    # Remove header if present
    if names and names[0].strip().lower() in ['name', 'team', 'team name']:
        names = names[1:]
    teams = [n.strip() for n in names if n.strip()]
    return teams

# Load the full DataFrame
@st.cache_data
def load_df():
    return pd.read_excel(EXCEL_PATH, engine='openpyxl')

# Save DataFrame to Excel
def save_df(df):
    df.to_excel(EXCEL_PATH, index=False, engine='openpyxl')

teams = load_teams()

# Sidebar navigation
st.sidebar.title('Navigation')
page = st.sidebar.radio('Go to', ['Update Points', 'View Points Table', 'Delete Date Range'])

st.title('Team Ranking Web App')

if page == 'Update Points':
    teams = load_teams()
    if not teams:
        st.warning('No teams found in the Excel file!')
        st.stop()

    # Date selection
    selected_date = st.date_input('Select Date', value=datetime.now().date())
    date_str = selected_date.strftime('%Y-%m-%d')

    # Points entry (default 20)
    points = st.number_input('Points', min_value=1, step=1, value=20)

    st.markdown('#### Participation & Rank')
    participation = {}
    rank_selection = {}
    cols = st.columns(2)
    rank_options = ['No Rank', '1st', '2nd', '3rd']
    for idx, team in enumerate(teams):
        with cols[idx % 2]:
            row = st.columns([2, 2])
            participation[team] = row[0].checkbox(team, value=True, key=f'part_{team}')
            rank_selection[team] = row[1].selectbox('Rank', rank_options, key=f'rank_{team}')

    if st.button('Submit'):
        # Collect participants and their ranks
        participants = [team for team in teams if participation[team]]
        if not participants:
            st.error('At least one participant must be selected.')
            st.stop()
        # Group by rank
        rank_groups = {'1st': [], '2nd': [], '3rd': []}
        for team in participants:
            r = rank_selection[team]
            if r in rank_groups:
                rank_groups[r].append(team)
        # Check for duplicate ranks (optional: allow multiple per rank)
        # Calculate points
        num_participants = len(participants)
        total_points = points * num_participants
        rank_shares = {'1st': 0.5, '2nd': 0.3, '3rd': 0.2}
        new_points = {}
        for team in teams:
            if not participation[team]:
                pts = 0
            else:
                assigned = False
                for rank, group in rank_groups.items():
                    if team in group and len(group) > 0:
                        pts = int((rank_shares[rank] * total_points) / len(group)) - points
                        assigned = True
                        break
                if not assigned:
                    pts = -points
            new_points[team] = pts
        # Load and update DataFrame
        df = load_df()
        # Add new date column if needed
        col_name = date_str
        if col_name in df.columns:
            suffix = 2
            while f"{date_str} ({suffix})" in df.columns:
                suffix += 1
            col_name = f"{date_str} ({suffix})"
        df[col_name] = 0
        # Ensure all teams are present in the DataFrame
        for team in teams:
            if team not in df['Name'].values:
                df = pd.concat([df, pd.DataFrame({'Name': [team]})], ignore_index=True)
        # Set points for each team
        for idx, row in df.iterrows():
            team = row['Name']
            if team in new_points:
                df.at[idx, col_name] = new_points[team]
            else:
                df.at[idx, col_name] = 0
        save_df(df)
        st.success(f'Points updated for {col_name}!')
        load_df.clear()
        load_teams.clear()
        st.rerun()
elif page == 'View Points Table':
    st.markdown('### Current Points Table')
    df = load_df()

    def highlight_balance(val):
        try:
            v = float(val)
        except:
            return ''
        if not v.is_integer():
            return ''
        if v > 0:
            return 'background-color: #b6fcb6; color: black;'
        elif v < 0:
            return 'background-color: #ffcccc; color: black;'
        else:
            return 'background-color: #e0e0e0; color: black;'

    def highlight_balance_col(col):
        return col.map(highlight_balance)

    # Replace decimal values in Balance with None
    def int_or_one_decimal(x):
        try:
            v = float(x)
            if v.is_integer():
                return str(int(v))
            else:
                return f"{v:.1f}"
        except:
            return x
    # Standardize date column headers to yyyy-mm-dd and handle duplicates
    import re
    from collections import Counter
    def fix_date_col(col):
        try:
            if re.match(r'\d{4}-\d{2}-\d{2}$', str(col)):
                return str(col)[:10]
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', str(col)):
                return str(col)[:10]
            import dateutil.parser
            dt = dateutil.parser.parse(str(col), dayfirst=False, yearfirst=False)
            return dt.strftime('%Y-%m-%d')
        except:
            return col
    new_cols = []
    date_count = Counter()
    for c in df.columns:
        if c not in ['Name', 'Balance']:
            base = fix_date_col(c)
            date_count[base] += 1
            if date_count[base] == 1:
                new_cols.append(base)
            else:
                new_cols.append(f"{base} ({date_count[base]})")
        else:
            new_cols.append(c)
    df.columns = new_cols
    # Recalculate Balance as the sum of all date columns
    date_cols = [c for c in df.columns if c not in ['Name', 'Balance']]
    df['Balance'] = df[date_cols].apply(lambda row: sum(pd.to_numeric(row, errors='coerce').fillna(0)), axis=1)
    # Format all columns except 'Name' as int or 1 decimal
    for col in df.columns:
        if col != 'Name':
            df[col] = df[col].apply(int_or_one_decimal)
    # Remove rows where Name is empty or None
    if 'Name' in df.columns:
        df = df[df['Name'].notnull() & (df['Name'].astype(str).str.strip() != '')]
    styled = df.style.apply(highlight_balance_col, subset=['Balance'])
    st.dataframe(styled, use_container_width=True)

    # Settlement calculation
    st.markdown('----')
    st.markdown('#### Suggested Settlements')
    # Prepare balances
    df_bal = df[['Name', 'Balance']].copy()
    df_bal['Balance'] = pd.to_numeric(df_bal['Balance'], errors='coerce').fillna(0)
    creditors = df_bal[df_bal['Balance'] > 0].sort_values('Balance', ascending=False).reset_index(drop=True)
    debtors = df_bal[df_bal['Balance'] < 0].sort_values('Balance').reset_index(drop=True)
    settlements = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor = debtors.loc[i]
        creditor = creditors.loc[j]
        give = min(-debtor['Balance'], creditor['Balance'])
        if give > 0:
            settlements.append(f"{debtor['Name']} transfers {creditor['Name']}: {give:.0f}")
            df_bal.loc[df_bal['Name'] == debtor['Name'], 'Balance'] += give
            df_bal.loc[df_bal['Name'] == creditor['Name'], 'Balance'] -= give
            # Update local copies for loop
            debtors.at[i, 'Balance'] += give
            creditors.at[j, 'Balance'] -= give
        if abs(debtors.at[i, 'Balance']) < 1e-6:
            i += 1
        if abs(creditors.at[j, 'Balance']) < 1e-6:
            j += 1
    if settlements:
        for s in settlements:
            st.write(s)
    else:
        st.write('All balances are already settled.')
elif page == 'Delete Date Range':
    st.markdown('### Delete Data by Date Range')
    df = load_df()
    # Find all date columns (exclude 'Name' and 'Balance')
    date_cols = [c for c in df.columns if c not in ['Name', 'Balance']]
    # Try to parse all date columns to datetime for filtering
    import re
    import dateutil.parser
    def parse_date_col(col):
        try:
            # Remove suffix if present (e.g., '2026-04-01 (2)')
            base = re.match(r'(\d{4}-\d{2}-\d{2})', str(col))
            if base:
                return datetime.strptime(base.group(1), '%Y-%m-%d').date()
            return dateutil.parser.parse(str(col)[:10]).date()
        except:
            return None
    parsed_dates = [(c, parse_date_col(c)) for c in date_cols]
    valid_dates = [d for c, d in parsed_dates if d is not None]
    if valid_dates:
        min_date = min(valid_dates)
        max_date = max(valid_dates)
    else:
        min_date = max_date = datetime.now().date()
    start_date = st.date_input('Start Date', value=min_date, min_value=min_date, max_value=max_date)
    end_date = st.date_input('End Date', value=max_date, min_value=min_date, max_value=max_date)
    if st.button('Delete Data in Range'):
        # Find columns to delete
        to_delete = [c for c, d in parsed_dates if d is not None and start_date <= d <= end_date]
        if not to_delete:
            st.info('No columns found in the selected date range.')
        else:
            df = df.drop(columns=to_delete)
            save_df(df)
            load_df.clear()
            st.success(f'Deleted columns: {to_delete}')
