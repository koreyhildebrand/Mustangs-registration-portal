import streamlit as st
import pandas as pd
import time


@st.cache_data(ttl=60)
def get_worksheet_data(ws_name: str) -> pd.DataFrame:
    """Load any worksheet with automatic 429 retry."""
    sheet = st.session_state.sheet
    try:
        ws = sheet.worksheet(ws_name)
        return pd.DataFrame(ws.get_all_records())
    except Exception as e:
        if "429" in str(e):
            time.sleep(10)
            return get_worksheet_data(ws_name)
        st.error(f"Error loading {ws_name}: {str(e)}")
        return pd.DataFrame()


@st.cache_data(ttl=60)
def get_live_equipment() -> pd.DataFrame:
    """Load Equipment sheet with default columns for new players."""
    df = get_worksheet_data("Equipment")
    required_cols = [
        "PlayerID", "First Name", "Last Name", "Helmet", "Helmet Size",
        "Shoulder Pads", "Shoulder Pads Size", "Pants w/Belt", "Pants Size",
        "Thigh Pads", "Tailbone Pad", "Knee Pads", "Secured Rental"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = False if col in ["Helmet", "Shoulder Pads", "Pants w/Belt",
                                       "Thigh Pads", "Tailbone Pad", "Knee Pads",
                                       "Secured Rental"] else ""
    return df
