import streamlit as st
import pandas as pd
from utils.sheets import get_worksheet_data   # ← This was the missing import


def show_football_operations(teams_df: pd.DataFrame, sheet, is_admin: bool):
    """Football Operations page – assign staff to teams."""
    st.header("⚙️ Football Operations")
    st.subheader("Assign Staff to Teams")

    if st.button("🔄 Refresh Teams & Staff", type="primary", width='stretch'):
        st.cache_data.clear()
        st.rerun()

    team_list = sorted(teams_df["TeamName"].dropna().unique().tolist()) if not teams_df.empty else []
    if not team_list:
        st.warning("No teams exist yet.")
        return

    selected_team = st.selectbox("Select Team", team_list, key="ops_team_select")
    team_row_idx = teams_df[teams_df["TeamName"] == selected_team].index
    team_row = teams_df.iloc[team_row_idx[0]] if len(team_row_idx) > 0 else None

    st.subheader(f"Current Staff for {selected_team}")
    if team_row is not None:
        st.write(f"**Head Coach:** {team_row.get('Coach', '—')}")
        st.write(f"**Assistant Coach(es):** {team_row.get('Assistant Coach', '—')}")
        st.write(f"**Team Manager:** {team_row.get('Team Manager', '—')}")
        st.write(f"**Trainer / Medical:** {team_row.get('Trainer', '—')}")

    st.subheader("Update / Assign Staff")
    with st.form("staff_form", clear_on_submit=False):
        # Get list of users who have Coach role
        coach_users_df = get_worksheet_data("Users")
        coach_users = coach_users_df[
            coach_users_df.get("roles", "").str.contains("Coach", case=False, na=False)
        ]["name"].dropna().unique().tolist()

        head_coach = st.selectbox("Head Coach", options=[""] + coach_users, key="head_coach_select")
        assistant_coaches = st.text_input(
            "Assistant Coach(es) - comma separated",
            value=team_row.get("Assistant Coach", "") if team_row is not None else ""
        )
        team_manager = st.selectbox("Team Manager", options=[""] + coach_users, key="manager_select")
        trainer = st.selectbox("Trainer / Medical Staff", options=[""] + coach_users, key="trainer_select")

        if st.form_submit_button("💾 Save Staff Assignments"):
            for col in ["Assistant Coach", "Team Manager", "Trainer"]:
                if col not in teams_df.columns:
                    teams_df[col] = ""
            idx = teams_df[teams_df["TeamName"] == selected_team].index[0]
            teams_df.at[idx, "Coach"] = head_coach.strip()
            teams_df.at[idx, "Assistant Coach"] = assistant_coaches.strip()
            teams_df.at[idx, "Team Manager"] = team_manager.strip()
            teams_df.at[idx, "Trainer"] = trainer.strip()

            sheet.worksheet("Teams").update([teams_df.columns.values.tolist()] + teams_df.fillna("").values.tolist())
            st.success(f"✅ Staff assignments saved for {selected_team}!")
            st.rerun()
