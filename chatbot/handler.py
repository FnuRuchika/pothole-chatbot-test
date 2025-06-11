import pandas as pd
import os
from geopy.distance import geodesic

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

# Load and clean data
df_311 = pd.read_csv(os.path.join(DATA_DIR, '311_data_cleaned.csv'))
df_311['Latitude'] = pd.to_numeric(df_311['Latitude'], errors='coerce')
df_311['Longitude'] = pd.to_numeric(df_311['Longitude'], errors='coerce')
df_311['OPENEDDATETIME'] = pd.to_datetime(df_311['OPENEDDATETIME'], errors='coerce')
df_311['CLOSEDDATETIME'] = pd.to_datetime(df_311['CLOSEDDATETIME'], errors='coerce')
df_311['fix_duration_days'] = (df_311['CLOSEDDATETIME'] - df_311['OPENEDDATETIME']).dt.days
df_311['Year'] = df_311['OPENEDDATETIME'].dt.year
df_311['Month'] = df_311['OPENEDDATETIME'].dt.to_period('M')

df_pavement = pd.read_csv(os.path.join(DATA_DIR, 'COSA_pavement_311.csv'))
df_weather = pd.read_csv(os.path.join(DATA_DIR, 'Potholes_Weather.csv'))
df_street = pd.read_csv(os.path.join(DATA_DIR, 'Street_IMP_Cleaned.csv'))

UTSA_COORDS = (29.5843, -98.6190)
IMPORTANT_ZONES = {
    "school": (29.5614, -98.6265),
    "hospital": (29.5085, -98.5756),
    "senior_center": (29.4931, -98.5412)
}

def handle_query(query):
    query = query.lower().strip()

    # 1. Active complaints near schools, hospitals, senior centers
    if any(kw in query for kw in ["school", "school zone", "senior", "senior center", "hospital", "near schools", "around hospitals", "active potholes near"]):
        try:
            active = df_311[df_311['CLOSEDDATETIME'].isna()].dropna(subset=['Latitude', 'Longitude'])
            results = []
            for label, coords in IMPORTANT_ZONES.items():
                active['distance_km'] = active.apply(
                    lambda row: geodesic((row['Latitude'], row['Longitude']), coords).km, axis=1
                )
                nearby = active[active['distance_km'] <= 0.5]
                results.append(f"🟡 {label.replace('_', ' ').title()}: {len(nearby)} active pothole complaints within 500 meters")
            return "\n".join(results)
        except:
            return "Error while analyzing active complaints near key locations."

    # 2. Top 10 most frequent complaint streets
    if any(kw in query for kw in ["top complaint", "most pothole", "top 10", "frequent pothole", "most reported", "most complained", "complaint streets", "top complaints", "where are potholes reported the most"]):
        try:
            top_streets = df_311['Street'].value_counts().head(10)
            lines = [f"{i+1}. {street} — {count} complaints" for i, (street, count) in enumerate(top_streets.items())]
            return "📍 Top 10 Most Frequently Reported Streets:\n\n" + "\n".join(lines)
        except:
            return "Something went wrong while identifying top complaint locations."

    # 3. Repeated pothole complaints on a street
    if any(kw in query for kw in ["repeated complaints", "complained before", "multiple complaints", "history", "is there a history", "have people complained", "are there repeated complaints"]):
        try:
            for street in df_311['Street'].dropna().unique():
                if street.lower() in query:
                    count = df_311[df_311['Street'].str.lower() == street.lower()].shape[0]
                    if count > 5:
                        return f"Yes — there have been {count} complaints on {street}."
                    elif count > 0:
                        return f"There have been {count} complaints on {street}, but not a frequent issue."
                    else:
                        return f"No complaints found on {street}."
            return "Can you clarify which road you're asking about?"
        except:
            return "I couldn’t process repeated complaints right now."

    # 4. Bus stops near roads with poor PCI
    if "bus stop" in query and any(term in query for term in ["pci", "bad road", "poor condition"]):
        try:
            bus_stops = df_street.dropna(subset=['Latitude', 'Longitude'])
            bad_roads = df_pavement[df_pavement['PCI'] < 40].dropna(subset=['Latitude', 'Longitude'])

            risky_stops = []
            for _, stop in bus_stops.iterrows():
                stop_loc = (stop['Latitude'], stop['Longitude'])
                for _, road in bad_roads.iterrows():
                    road_loc = (road['Latitude'], road['Longitude'])
                    if geodesic(stop_loc, road_loc).meters <= 200:
                        risky_stops.append(stop.get('StopID', 'Unknown'))

            if risky_stops:
                return f"⚠️ {len(set(risky_stops))} bus stops are near roads with poor PCI scores."
            else:
                return "No bus stops found near poor PCI roads."
        except:
            return "Could not evaluate bus stop risk. Columns may be missing."

    # 5. Preventive patching before rain
    if any(kw in query for kw in ["preventive patch", "prioritize patching", "before rain"]):
        try:
            low_pci_roads = df_pavement[df_pavement['PCI'] < 40]
            repeat_complaints = df_311['Street'].value_counts()
            repeated_streets = repeat_complaints[repeat_complaints > 5].index.tolist()

            suggestions = []
            for _, row in low_pci_roads.iterrows():
                street = row.get('MSAG_Name')
                if street and street in repeated_streets:
                    suggestions.append(f"{street} (PCI: {int(row['PCI'])})")

            if suggestions:
                top_suggestions = suggestions[:5]
                return "🛠️ Suggested streets for preventative patching before the next rain:\n\n" + "\n".join(top_suggestions)
            else:
                return "No streets found that meet both poor PCI and repeated complaints."
        except:
            return "Couldn’t analyze preventive patching priorities right now."

    # Existing answers
    if "worst pci" in query or "bad roads" in query or "poor condition" in query:
        try:
            poor_roads = df_pavement[df_pavement['PCI'] < 40]
            top5 = poor_roads[['MSAG_Name', 'FromStreet', 'ToStreet', 'PCI']].dropna().sort_values(by='PCI').head(5)
            roads = [
                f"{row['MSAG_Name']} from {row['FromStreet']} to {row['ToStreet']} (PCI: {int(row['PCI'])})"
                for _, row in top5.iterrows()
            ]
            return "Here are 5 roads with the worst pavement conditions:\n\n" + "\n".join(roads)
        except:
            return "Couldn't process PCI data right now."

    if any(kw in query for kw in ["increase", "trend", "more potholes", "complaints rising"]):
        try:
            yearly = df_311['Year'].value_counts().sort_index()
            if len(yearly) < 2:
                return "Not enough data to determine a trend."

            current_year = yearly.index[-1]
            prev_year = yearly.index[-2]
            diff = yearly[current_year] - yearly[prev_year]
            percent = round((diff / yearly[prev_year]) * 100, 1)

            if diff > 0:
                return f"Yes — pothole complaints increased by **{percent}%** from {prev_year} to {current_year}."
            elif diff < 0:
                return f"No — complaints decreased by **{abs(percent)}%** from {prev_year} to {current_year}."
            else:
                return f"Pothole complaints stayed the same from {prev_year} to {current_year}."
        except:
            return "I'm unable to analyze the trend right now."

    if any(kw in query for kw in ["how long", "repair time", "fixed quickly", "time to fix", "average fix", "potholes get fixed"]):
        valid_durations = df_311['fix_duration_days'].dropna()
        avg_days = round(valid_durations.mean(), 1)
        return f"On average, potholes take about **{avg_days} days** to get fixed in San Antonio."

    if "how many potholes" in query:
        count = len(df_311)
        return f"There are approximately {count:,} reported pothole complaints in the city."

    if "most potholes" in query or "highest amount" in query:
        if 'Council District' in df_311.columns:
            top = df_311['Council District'].value_counts().idxmax()
            return f"Council District {top} has the highest number of reported potholes."
        else:
            return "District data isn't available."

    if "utsa" in query or "near utsa" in query:
        nearby = df_311.dropna(subset=['Latitude', 'Longitude'])
        nearby['distance_km'] = nearby.apply(
            lambda row: geodesic((row['Latitude'], row['Longitude']), UTSA_COORDS).km,
            axis=1
        )
        close_potholes = nearby[nearby['distance_km'] <= 1.0]
        return f"There are {len(close_potholes)} pothole complaints within 1 km of UTSA."

    return "I'm still learning! Try asking about pothole counts, UTSA, PCI scores, or complaint history."
