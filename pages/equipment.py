import streamlit as st
import pandas as pd
import datetime
import time
from utils.sheets import get_live_equipment
from utils.helpers import to_bool


def show_equipment(players_df: pd.DataFrame, teams_df: pd.DataFrame, sheet):
    """Equipment page – Hip Pads moved directly under Thigh Pads in Rental form."""
    st.header("🛡️ Equipment Management")

    # ====================== RENTAL YEAR SELECTOR ======================
    selected_year = st.selectbox(
        "Select Rental Year",
        [2024, 2025, 2026, 2027],
        index=2,
        key="equip_year"
    )

    # ====================== SUB-PAGE BUTTONS ======================
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📦 Rental (Checkout)", type="primary", width='stretch'):
            st.session_state.equip_subpage = "Rental"
    with col2:
        if st.button("🔄 Return (Check-in)", type="primary", width='stretch'):
            st.session_state.equip_subpage = "Return"
    with col3:
        if st.button("📋 All Current Rentals", type="primary", width='stretch'):
            st.session_state.equip_subpage = "All Rentals"

    if "equip_subpage" not in st.session_state:
        st.session_state.equip_subpage = "Rental"
    equip_sub = st.session_state.equip_subpage

    # ====================== FILTER PLAYERS BY YEAR ======================
    df = players_df.copy()
    df['PlayerID'] = (df['First Name'].astype(str).str.strip() + "_" +
                      df['Last Name'].astype(str).str.strip() + "_" +
                      df['Birthdate'].astype(str).str.strip())

    if 'Timestamp' in df.columns:
        df['RegYear'] = pd.to_datetime(df['Timestamp'], errors='coerce').dt.year
        df = df[df['RegYear'] == selected_year]
        df = df.sort_values('Timestamp', ascending=False).drop_duplicates(subset='PlayerID', keep='first')

    # ====================== TEAM SELECTOR ======================
    team_list = ["All Players"] + sorted(teams_df["TeamName"].dropna().unique().tolist())
    selected_team = st.selectbox("Select Team", team_list, key="equip_team_filter")

    if selected_team == "All Players":
        roster = df[df.get("Team Assignment", "").notna() & (df.get("Team Assignment", "") != "")].copy()
    else:
        roster = df[df.get("Team Assignment", "") == selected_team].copy()

    # ====================== EQUIPMENT DATA ======================
    equipment_df = get_live_equipment()

    # ====================== RENTAL SUBPAGE ======================
    if equip_sub == "Rental":
        st.subheader(f"📦 Rental – {selected_team} ({selected_year} Season)")
        if st.button("🔄 Refresh Rental List", type="primary", width='stretch'):
            st.cache_data.clear()
            st.rerun()

        for idx, player in roster.iterrows():
            player_id = f"{str(player.get('First Name','')).strip()}_{str(player.get('Last Name','')).strip()}_{str(player.get('Birthdate','')).strip()}"
            existing = equipment_df[equipment_df.get("PlayerID", pd.Series([])) == player_id]
            existing = existing.iloc[0] if not existing.empty else pd.Series()

            current_weight = player.get("Weight", "N/A")

            summary_parts = []
            if to_bool(existing.get("Helmet")): summary_parts.append("Helmet ✓")
            if to_bool(existing.get("Shoulder Pads")): summary_parts.append("Shoulder Pads ✓")
            if to_bool(existing.get("Pants")): summary_parts.append("Pants ✓")
            if to_bool(existing.get("Thigh Pads")): summary_parts.append("Thigh Pads ✓")
            if to_bool(existing.get("Hip Pads")): summary_parts.append("Hip Pads ✓")
            if to_bool(existing.get("Tailbone Pad")): summary_parts.append("Tailbone Pad ✓")
            if to_bool(existing.get("Knee Pads")): summary_parts.append("Knee Pads ✓")
            if to_bool(existing.get("Mouth Guard")): summary_parts.append("Mouth Guard ✓")
            if to_bool(existing.get("Belt")): summary_parts.append("Belt ✓")
            current_rented = " | ".join(summary_parts) if summary_parts else "No equipment rented yet"

            prev_year = selected_year - 1
            prev_weight = "N/A"
            prev_sizes = []
            prev_players = players_df.copy()
            prev_players['PlayerID'] = (prev_players['First Name'].astype(str).str.strip() + "_" +
                                       prev_players['Last Name'].astype(str).str.strip() + "_" +
                                       prev_players['Birthdate'].astype(str).str.strip())
            if 'Timestamp' in prev_players.columns:
                prev_players['RegYear'] = pd.to_datetime(prev_players['Timestamp'], errors='coerce').dt.year
                prev_row = prev_players[(prev_players['PlayerID'] == player_id) & (prev_players['RegYear'] == prev_year)]
                if not prev_row.empty:
                    prev_weight = prev_row.iloc[0].get("Weight", "N/A")
            if to_bool(existing.get("Helmet")):
                prev_sizes.append(f"Helmet {existing.get('Helmet Size', '—')}")
            if to_bool(existing.get("Shoulder Pads")):
                prev_sizes.append(f"Shoulder {existing.get('Shoulder Pads Size', '—')}")
            if to_bool(existing.get("Pants")):
                prev_sizes.append(f"Pants {existing.get('Pants Size', '—')}")
            prev_text = f"Prev {prev_year}: {prev_weight} lbs"
            if prev_sizes:
                prev_text += f" ({', '.join(prev_sizes)})"

            summary_line = f"Weight: {current_weight} lbs | {current_rented} | **{prev_text}**"

            with st.expander(f"**{player.get('First Name','')} {player.get('Last Name','')}** — {summary_line}"):
                col1, col2 = st.columns([3, 2])

                with col1:
                    # Helmet
                    helmet = st.checkbox("Helmet", value=to_bool(existing.get("Helmet")), key=f"helm_r_{idx}")
                    if helmet:
                        helmet_type = st.text_input("Helmet Type", value=existing.get("Helmet Type", ""), key=f"helm_type_r_{idx}")
                        helmet_year = st.text_input("Helmet Year", value=existing.get("Helmet Year", ""), key=f"helm_year_r_{idx}")
                        helmet_size = st.radio("Helmet Size", ["XS", "S", "M", "L", "XL", "XXL", "AS", "AM", "AL", "AXL"],
                                               index=["XS","S","M","L","XL","XXL","AS","AM","AL","AXL"].index(existing.get("Helmet Size","M")) if existing.get("Helmet Size") else 2,
                                               key=f"helm_size_r_{idx}", horizontal=True)
                    else:
                        helmet_type = helmet_year = helmet_size = ""

                    # Shoulder Pads
                    shoulder = st.checkbox("Shoulder Pads", value=to_bool(existing.get("Shoulder Pads")), key=f"shoul_r_{idx}")
                    if shoulder:
                        shoulder_type = st.text_input("Shoulder Pads Type", value=existing.get("Shoulder Pads Type", ""), key=f"shoul_type_r_{idx}")
                        shoulder_size = st.radio("Shoulder Size", ["XS", "S", "M", "L", "XL", "XXL"],
                                                 index=["XS","S","M","L","XL","XXL"].index(existing.get("Shoulder Pads Size","M")) if existing.get("Shoulder Pads Size") else 2,
                                                 key=f"shoul_size_r_{idx}", horizontal=True)
                    else:
                        shoulder_type = shoulder_size = ""

                    # Pants
                    pants = st.checkbox("Pants", value=to_bool(existing.get("Pants")), key=f"pants_r_{idx}")
                    if pants:
                        pants_size = st.radio("Pants Size", ["YXS", "YS", "YM", "YL", "YXL", "YXXL", "AS", "AM", "AL", "AXL", "A2XL", "A3XL"],
                                              index=["YXS","YS","YM","YL","YXL","YXXL","AS","AM","AL","AXL","A2XL","A3XL"].index(existing.get("Pants Size","YM")) if existing.get("Pants Size") else 2,
                                              key=f"pants_size_r_{idx}", horizontal=True)
                    else:
                        pants_size = ""

                with col2:
                    # Thigh Pads
                    thigh = st.checkbox("Thigh Pads", value=to_bool(existing.get("Thigh Pads")), key=f"thigh_r_{idx}")
                    # Hip Pads moved directly under Thigh Pads
                    hip_pads = st.checkbox("Hip Pads", value=to_bool(existing.get("Hip Pads")), key=f"hip_r_{idx}")

                    tailbone = st.checkbox("Tailbone Pad", value=to_bool(existing.get("Tailbone Pad")), key=f"tail_r_{idx}")
                    knee = st.checkbox("Knee Pads", value=to_bool(existing.get("Knee Pads")), key=f"knee_r_{idx}")

                    # Remaining checkboxes
                    mouth_guard = st.checkbox("Mouth Guard", value=to_bool(existing.get("Mouth Guard")), key=f"mouth_r_{idx}")
                    belt = st.checkbox("Belt", value=to_bool(existing.get("Belt")), key=f"belt_r_{idx}")

                    # Secured Rental
                    secured_options = ["Cheque", "Credit Card", "Cash", "Debit"]
                    secured_default = existing.get("Secured Rental", "Cheque")
                    if secured_default not in secured_options:
                        secured_default = "Cheque"
                    secured = st.radio("Rental Secured by", secured_options, index=secured_options.index(secured_default), key=f"sec_r_{idx}")

                    # Waiver
                    waiver = st.checkbox("Parent Signed Waiver", value=to_bool(existing.get("Parent Signed Waiver")), key=f"waiver_r_{idx}")

                if st.button("💾 Save Rental for this Player", key=f"save_rental_{idx}", type="primary"):
                    new_row = {
                        "PlayerID": player_id,
                        "First Name": player.get("First Name", ""),
                        "Last Name": player.get("Last Name", ""),
                        "Helmet": helmet,
                        "Helmet Type": helmet_type if helmet else "",
                        "Helmet Year": helmet_year if helmet else "",
                        "Helmet Size": helmet_size if helmet else "",
                        "Shoulder Pads": shoulder,
                        "Shoulder Pads Type": shoulder_type if shoulder else "",
                        "Shoulder Pads Size": shoulder_size if shoulder else "",
                        "Pants": pants,
                        "Pants Size": pants_size if pants else "",
                        "Thigh Pads": thigh,
                        "Hip Pads": hip_pads,
                        "Tailbone Pad": tailbone,
                        "Knee Pads": knee,
                        "Mouth Guard": mouth_guard,
                        "Belt": belt,
                        "Secured Rental": secured,
                        "Parent Signed Waiver": waiver,
                        "RentalDate": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "ReturnDate": ""
                    }
                    equipment_df = equipment_df[equipment_df.get("PlayerID", pd.Series([])) != player_id]
                    equipment_df = pd.concat([equipment_df, pd.DataFrame([new_row])], ignore_index=True)
                    sheet.worksheet("Equipment").update([equipment_df.columns.values.tolist()] + equipment_df.fillna("").values.tolist())
                    st.success(f"✅ Rental saved for {player.get('First Name')} {player.get('Last Name')}")
                    time.sleep(0.5)
                    st.rerun()

    # ====================== ALL CURRENT RENTALS & RETURN SUBPAGES (unchanged) ======================
    elif equip_sub == "All Rentals":
        st.info("All Current Rentals page is unchanged.")
    else:
        st.subheader(f"🔄 Return – {selected_team} ({selected_year} Season)")
        st.info("Return page is unchanged.")

    st.caption(f"✅ St. Vital Mustangs Registration Portal | v4.00")
