import streamlit as st
import pandas as pd


def show_restricted_health(players_df: pd.DataFrame, teams_df: pd.DataFrame, can_see_all_teams: bool, allowed_teams: list):
    st.header("🔒 Restricted Health Data")

    # Team selector
    if can_see_all_teams:
        team_options = ["All Teams"] + sorted(teams_df["TeamName"].dropna().unique().tolist())
    else:
        team_options = sorted([t for t in teams_df["TeamName"].dropna().unique().tolist() if t in allowed_teams])

    selected_team = st.selectbox("Select Team to View", team_options, key="restricted_team")

    if selected_team == "All Teams":
        roster = players_df.copy()
    else:
        roster = players_df[players_df.get("Team Assignment", "") == selected_team].copy()

    if roster.empty:
        st.info("No players found for the selected team.")
        return

    st.subheader(f"Roster for {selected_team}")

    # Robust lookup for the two new medical columns
    details_col = None
    medications_col = None
    for col in roster.columns:
        col_str = str(col).lower()
        if "provide details" in col_str or "medications, allergies" in col_str:
            details_col = col
        if "please list medications" in col_str or "list medications" in col_str:
            medications_col = col

    for _, player in roster.iterrows():
        alerts = []
        if player.get("Does your player have a History of Concussions?") == "Yes":
            alerts.append("Concussion")
        if str(player.get("Does your player have Allergies?", "")).strip() not in ["", "nan", "None", "N/A"]:
            alerts.append("Allergies")
        if player.get("Does your player have Epilepsy?") == "Yes":
            alerts.append("Epilepsy")
        if player.get("Does your player have a Heart Condition?") == "Yes":
            alerts.append("Heart Condition")
        if player.get("Is your player a Diabetic?") == "Yes":
            alerts.append("Diabetic")

        alert_text = " | ".join(alerts) if alerts else ""

        with st.expander(f"{player.get('First Name','')} {player.get('Last Name','')} {'⚠️ ' + alert_text if alert_text else ''}"):
            if alert_text:
                st.error(f"**MEDICAL ALERT:** {alert_text}")

            st.write(f"**Birthdate:** {player.get('Birthdate', 'N/A')}")
            st.write(f"**MB Health Number:** {player.get('MB Health Number:', 'N/A')}")
            st.write(f"**History of Concussions:** {player.get('Does your player have a History of Concussions?', 'No')}")
            st.write(f"**Allergies:** {player.get('Does your player have Allergies?', 'None')}")
            st.write(f"**Epilepsy:** {player.get('Does your player have Epilepsy?', 'No')}")
            st.write(f"**Heart Condition:** {player.get('Does your player have a Heart Condition?', 'No')}")
            st.write(f"**Diabetic:** {player.get('Is your player a Diabetic?', 'No')}")
            st.write(f"**Asthma:** {player.get('Does your player have Asthma?', 'No')}")
            st.write(f"**Medication:** {player.get('Does your player take any Medications?', 'None')}")

            # NEW: Added the two requested columns
            if details_col and details_col in player:
                details = str(player[details_col]).strip()
                if details and details.lower() not in ["", "nan", "none", "n/a"]:
                    st.write(f"**Medical Details / Medications / Allergies:** {details}")

            if medications_col and medications_col in player:
                meds = str(player[medications_col]).strip()
                if meds and meds.lower() not in ["", "nan", "none", "n/a"]:
                    st.write(f"**Please list medications:** {meds}")

    st.caption("✅ Restricted Health Data")
