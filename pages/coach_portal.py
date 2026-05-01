import streamlit as st
import pandas as pd
import datetime
from utils.helpers import calculate_age_group


def show_coach_portal(players_df: pd.DataFrame, teams_df: pd.DataFrame, name: str, is_admin: bool):
    st.header("🏈 Coach Portal")
    st.subheader(f"Welcome, {name}")

    # ====================== DYNAMIC CURRENT YEAR ======================
    if 'Timestamp' in players_df.columns and not players_df.empty:
        temp = players_df.copy()
        temp['RegYear'] = pd.to_datetime(temp['Timestamp'], errors='coerce').dt.year
        current_year = int(temp['RegYear'].max()) if not temp['RegYear'].isna().all() else datetime.datetime.now().year
    else:
        current_year = datetime.datetime.now().year

    if st.button("🔄 Refresh My Teams", type="primary", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    # ====================== FILTER PLAYERS TO CURRENT YEAR ONLY ======================
    df = players_df.copy()
    df['PlayerID'] = (df['First Name'].astype(str).str.strip() + "_" +
                      df['Last Name'].astype(str).str.strip() + "_" +
                      df['Birthdate'].astype(str).str.strip())

    if 'Timestamp' in df.columns:
        df['RegYear'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.year
        df = df[df['RegYear'] == current_year]
        df = df.sort_values('Timestamp', ascending=False).drop_duplicates(subset='PlayerID', keep='first')

    # ====================== MY TEAMS (only current year) ======================
    if is_admin:
        my_teams = sorted(df["Team Assignment"].dropna().unique().tolist())
    else:
        coached_teams = teams_df[
            teams_df.get("Coach", "").str.contains(name, case=False, na=False)
        ]["TeamName"].tolist()
        
        my_teams = [team for team in coached_teams if team in df["Team Assignment"].values]

    if not my_teams:
        st.warning(f"You are not currently assigned as coach to any team in the {current_year} season.")
        return

    selected_team = st.selectbox("Select Team to View", sorted(my_teams), key="coach_team_select")

    # ====================== ROSTER ======================
    coach_roster = df[df.get("
