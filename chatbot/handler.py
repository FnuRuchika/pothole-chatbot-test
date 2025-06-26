import os
from dotenv import load_dotenv
import pandas as pd
from geopy.distance import geodesic
from chatbot.llm_groq import ask_groq

# Load .env variables
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, '..', 'data')

# Load and clean datasets
df_311 = pd.read_csv(os.path.join(DATA_DIR, '311_Data_Cleaned.csv'))
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

    try:
        if any(kw in query for kw in ["school", "hospital", "senior center", "active potholes near"]):
            active = df_311[df_311['CLOSEDDATETIME'].isna()].dropna(subset=['Latitude', 'Longitude'])
            results = []
            for label, coords in IMPORTANT_ZONES.items():
                active['distance_km'] = active.apply(lambda row: geodesic((row['Latitude'], row['Longitude']), coords).km, axis=1)
                nearby = active[active['distance_km'] <= 0.5]
                results.append(f"🟡 {label.replace('_', ' ').title()}: {len(nearby)} active pothole complaints within 500 meters")
            return "\n".join(results)
    except:
        pass

    try:
        if any(kw in query for kw in ["top complaint", "most pothole", "top 10", "frequent pothole"]):
            top_streets = df_311['SUBJECTNAME'].value_counts().head(10)
            lines = [f"{i+1}. {street} — {count} complaints" for i, (street, count) in enumerate(top_streets.items())]
            return "📍 Top 10 Most Frequently Reported Streets:\n\n" + "\n".join(lines)
    except:
        pass

    try:
        if any(kw in query for kw in ["repeated complaints", "complained before", "history", "have people complained"]):
            for street in df_311['Street'].dropna().unique():
                if street.lower() in query:
                    count = df_311[df_311['SUBJECTNAME'].str.lower() == street.lower()].shape[0]
                    return f"Yes — {count} complaints found on {street}." if count > 5 else f"There are {count} complaints on {street}."
            return "Can you clarify which road you're asking about?"
    except:
        pass

    try:
        if "bus stop" in query and any(term in query for term in ["pci", "bad road", "poor condition"]):
            bus_stops = df_pavement[df_pavement['PCI'] > 40].dropna(subset=['Latitude', 'Longitude'])
            bad_roads = df_pavement[df_pavement['PCI'] < 40].dropna(subset=['Latitude', 'Longitude'])
            risky_stops = []
            for _, stop in bus_stops.iterrows():
                stop_loc = (stop['Latitude'], stop['Longitude'])
                for _, road in bad_roads.iterrows():
                    road_loc = (road['Latitude'], road['Longitude'])
                    if geodesic(stop_loc, road_loc).meters <= 200:
                        risky_stops.append(stop.get('StopID', 'Unknown'))
            return f"⚠️ {len(set(risky_stops))} bus stops are near roads with poor PCI scores." if risky_stops else "No bus stops found near poor PCI roads."
    except:
        pass

    try:
        if any(kw in query for kw in ["preventive patch", "before rain"]):
            low_pci_roads = df_pavement[df_pavement['PCI'] < 40]
            repeat_complaints = df_311['Street'].value_counts()
            repeated_streets = repeat_complaints[repeat_complaints > 5].index.tolist()
            suggestions = [f"{row['MSAG_Name']} (PCI: {int(row['PCI'])})" for _, row in low_pci_roads.iterrows() if row.get('MSAG_Name') in repeated_streets]
            return "🛠️ Suggested streets for preventative patching:\n\n" + "\n".join(suggestions[:5]) if suggestions else "No matching streets found."
    except:
        pass

    try:
        if "worst pci" in query or "bad roads" in query:
            poor_roads = df_pavement[df_pavement['PCI'] < 40]
            top5 = poor_roads[['MSAG_Name', 'FromStreet', 'ToStreet', 'PCI']].dropna().sort_values(by='PCI').head(5)
            roads = [f"{row['MSAG_Name']} from {row['FromStreet']} to {row['ToStreet']} (PCI: {int(row['PCI'])})" for _, row in top5.iterrows()]
            return "Here are 5 roads with the worst pavement conditions:\n\n" + "\n".join(roads)
    except:
        pass

    try:
        if any(kw in query for kw in ["increase", "trend", "more potholes"]):
            yearly = df_311['Year'].value_counts().sort_index()
            if len(yearly) >= 2:
                current_year, prev_year = yearly.index[-1], yearly.index[-2]
                diff = yearly[current_year] - yearly[prev_year]
                percent = round((diff / yearly[prev_year]) * 100, 1)
                return f"Yes — pothole complaints increased by **{percent}%** from {prev_year} to {current_year}." if diff > 0 else f"No — complaints decreased by **{abs(percent)}%**."
    except:
        pass

    try:
        if any(kw in query for kw in ["how long", "repair time", "average fix"]):
            avg_days = round(df_311['fix_duration_days'].dropna().mean(), 1)
            base_answer = f"On average, potholes take about **{avg_days} days** to get fixed in San Antonio."
            explanation = ask_groq("Why might pothole repair take this long?", context=base_answer)
            return f"{base_answer}\n\n💬 *Explanation:* {explanation}"
    except:
        pass

    try:
        if "how many potholes" in query:
            return f"There are approximately {len(df_311):,} reported pothole complaints in the city."
    except:
        pass

    try:
        if "most potholes" in query or "highest amount" in query:
            if 'Council District' in df_311.columns:
                top = df_311['Council District'].dropna().value_counts().idxmax()
                return f"Council District {top} has the highest number of reported potholes."
            else:
                return "District data isn't available."
    except:
        pass

    try:
        if "utsa" in query:
            nearby = df_311.dropna(subset=['Latitude', 'Longitude'])
            nearby['distance_km'] = nearby.apply(lambda row: geodesic((row['Latitude'], row['Longitude']), UTSA_COORDS).km, axis=1)
            close_potholes = nearby[nearby['distance_km'] <= 1.0]
            return f"There are {len(close_potholes)} pothole complaints within 1 km of UTSA."
    except:
        pass

    # If no rule matches or all failed —> Groq fallback
    return ask_groq(query)
