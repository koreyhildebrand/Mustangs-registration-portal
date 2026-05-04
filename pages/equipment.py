import streamlit as st
import pandas as pd
import datetime
import time
from utils.sheets import get_live_equipment
from utils.helpers import to_bool


def show_equipment(players_df: pd.DataFrame, teams_df: pd.DataFrame, sheet):
    """Equipment page – Added Private Rental feature"""
    st.header("🛡️ Equipment Management")

    # ====================== SUB-PAGE BUTTONS ======================
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📦 Rental (Checkout)", type="primary"):
            st.session_state.equip_subpage = "Rental"
    with col2:
        if st.button("📋 All Current Rentals", type="primary"):
            st.session_state.equip_subpage = "All Rentals"
    with col3:
        if st.button("➕ Private Rental", type="primary"):
            st.session_state.equip_subpage = "Private Rental"

    if "equip_subpage" not in st.session_state:
        st.session_state.equip_subpage = "Rental"
    equip_sub = st.session_state.equip_subpage

    # ====================== PRIVATE RENTAL TAB ======================
    if equip_sub == "Private Rental":
        st.subheader("➕ Create Private Rental Player")
        st.caption("These players are for equipment rental only and are NOT added to the main Players sheet.")

        with st.form("private_rental_form"):
            first_name = st.text_input("First Name *", key="pr_first")
            last_name = st.text_input("Last Name *", key="pr_last")
            birthdate = st.date_input("Birthdate (optional)", value=None, key="pr_birthdate")
            phone = st.text_input("Phone Number (optional)", key="pr_phone")

            submitted = st.form_submit_button("Create Private Rental Player")

            if submitted:
                if not first_name or not last_name:
                    st.error("First Name and Last Name are required.")
                else:
                    player_id = f"Private_{first_name.strip()}_{last_name.strip()}_{str(birthdate) if birthdate else 'N/A'}"

                    new_row = {
                        "PlayerID": player_id,
                        "First Name": first_name.strip(),
                        "Last Name": last_name.strip(),
                        "Birthdate": str(birthdate) if birthdate else "",
                        "Phone": phone.strip() if phone else "",
                        "Team Assignment": "Private Rental",
                        "Helmet": False,
                        "Shoulder Pads": False,
                        "Pants": False,
                        "Thigh Pads": False,
                        "Hip Pads": False,
                        "Tailbone Pad": False,
                        "Knee Pads": False,
                        "Mouth Guard": False,
                        "Belt": False,
                        "Practice Jersey Red": False,
                        "Practice Jersey Black": False,
                        "Practice Jersey White": False,
                        "RentalDate": "",
                        "ReturnDate": ""
                    }

                    equipment_df = get_live_equipment()
                    equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)

                    sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())

                    st.success(f"✅ Private rental player '{first_name} {last_name}' created successfully! They will now appear in the Rental list under 'Private Rental'.")
                    time.sleep(1)
                    st.rerun()

        return  # End Private Rental tab

    # ====================== REGULAR EQUIPMENT CODE (your existing logic) ======================
    selected_year = st.selectbox(
        "Select Rental Year",
        [2024, 2025, 2026, 2027],
        index=2,
        key="equip_year"
    )

    df = players_df.copy()
    df['PlayerID'] = (df['First Name'].astype(str).str.strip() + "_" +
                      df['Last Name'].astype(str).str.strip() + "_" +
                      df['Birthdate'].astype(str).str.strip())

    if 'Timestamp' in df.columns:
        df['RegYear'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.year
        df = df[df['RegYear'] == selected_year]
        df = df.sort_values('Timestamp', ascending=False).drop_duplicates(subset='PlayerID', keep='first')

    team_list = ["All Players"] + sorted(teams_df["TeamName"].dropna().unique().tolist())
    selected_team = st.selectbox("Select Team", team_list, key="equip_team_filter")

    if selected_team == "All Players":
        roster = df[df.get("Team Assignment", "").notna() & (df.get("Team Assignment", "") != "")].copy()
    else:
        roster = df[df.get("Team Assignment", "") == selected_team].copy()

    equipment_df = get_live_equipment()

    if equip_sub == "Rental":
        st.subheader(f"📦 Rental / Return – {selected_team} ({selected_year} Season)")
        if st.button("🔄 Refresh List", type="primary"):
            st.cache_data.clear()
            st.rerun()

        for idx, player in roster.iterrows():
            player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
            existing = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]
            existing = existing.iloc[0] if not existing.empty else pd.Series()

            current_weight = player.get("Weight", "N/A")

            # Previous year weight
            prev_year = selected_year - 1
            prev_weight = "N/A"
            prev_players = players_df.copy()
            prev_players['PlayerID'] = (prev_players['First Name'].astype(str).str.strip() + "_" +
                                       prev_players['Last Name'].astype(str).str.strip() + "_" +
                                       prev_players['Birthdate'].astype(str).str.strip())

            if 'Timestamp' in prev_players.columns:
                prev_players['RegYear'] = pd.to_datetime(prev_players['Timestamp'], errors='coerce').dt.year
                prev_row = prev_players[(prev_players['PlayerID'] == player_id) & (prev_players['RegYear'] == prev_year)]
                if not prev_row.empty:
                    prev_weight = prev_row.iloc[0].get("Weight", "N/A")

            # Last rental sizes
            last_rental_sizes = []
            last_equip = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]
            if not last_equip.empty:
                last_equip = last_equip.copy()
                if 'RentalDate' in last_equip.columns:
                    last_equip['RentalDate'] = pd.to_datetime(last_equip['RentalDate'], errors='coerce')
                    last_equip = last_equip.sort_values('RentalDate', ascending=False)
                last_row = last_equip.iloc[0]

                if pd.notna(last_row.get('Helmet Size')) and str(last_row.get('Helmet Size', '')).strip() != "":
                    last_rental_sizes.append(f"Helmet {last_row.get('Helmet Size', '—')}")
                if pd.notna(last_row.get('Shoulder Pads Size')) and str(last_row.get('Shoulder Pads Size', '')).strip() != "":
                    last_rental_sizes.append(f"Shoulder {last_row.get('Shoulder Pads Size', '—')}")
                if
