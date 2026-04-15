import pandas as pd
import datetime


def to_bool(val) -> bool:
    """Convert various truthy values to boolean safely."""
    if pd.isna(val) or val == "" or val is None:
        return False
    return str(val).strip().lower() in ["true", "1", "yes", "t"]


def calculate_age_group(dob_str: str, season_year: int) -> str:
    """Calculate age group (U10/U12/etc.) for a given season year."""
    try:
        dob_str = str(dob_str).strip()
        if '/' in dob_str:
            dob = datetime.datetime.strptime(dob_str, "%m/%d/%Y").date()
        else:
            dob = datetime.datetime.strptime(dob_str.split()[0], "%Y-%m-%d").date()
        age = season_year - dob.year
        if 9 <= age <= 10:   return "U10"
        elif 11 <= age <= 12: return "U12"
        elif 13 <= age <= 14: return "U14"
        elif 15 <= age <= 16: return "U16"
        elif 17 <= age <= 18: return "U18"
        elif age >= 19:      return "Major"
        return f"Outside {season_year}"
    except:
        return "Invalid"


def filter_by_team(df: pd.DataFrame, can_see_all_teams: bool, allowed_teams: list) -> pd.DataFrame:
    """Filter DataFrame by user's allowed teams."""
    if can_see_all_teams or df.empty:
        return df
    if "Team Assignment" in df.columns:
        return df[df["Team Assignment"].isin(allowed_teams)]
    return df
