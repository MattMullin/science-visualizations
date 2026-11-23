"""Rebuild the 180-idea editorial backlog without changing project status."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backlog.json"

TOPICS = {
    "atmosphere": [
        "Saharan Dust", "Atmospheric Rivers", "Jet Streams", "Tropical Cyclone Tracks",
        "Lightning Hotspots", "Ozone Hole", "Wildfire Smoke", "Monsoon Rainbands",
        "Polar Vortex", "Cloud Fraction", "Global Precipitation", "Severe Storm Tracks",
        "Aerosol Optical Depth", "Carbon Monoxide Plumes", "Nitrogen Dioxide Cities",
        "Methane Hotspots", "Surface Wind Fields", "Rossby Waves", "Hadley Circulation",
        "Sea Breeze Fronts", "Fog Formation", "Snowfall Bands", "Heat Domes",
        "Drought Severity", "Hail Climatology", "Air Temperature Anomalies",
        "Water Vapor Transport", "Stratospheric Temperature", "Volcanic Ash Transport",
        "Surface Solar Radiation",
    ],
    "ocean": [
        "Ocean Currents", "Sea Surface Temperature", "Ocean Heat Content",
        "Sea Level Anomalies", "Coastal Upwelling", "Marine Heatwaves",
        "Chlorophyll Blooms", "Ocean Salinity", "Gulf Stream Meanders",
        "Antarctic Circumpolar Current", "Tide Propagation", "Wave Heights",
        "Hurricane Ocean Cooling", "El Nino", "La Nina", "Ocean Acidification",
        "Dissolved Oxygen", "Argo Float Journeys", "Coral Bleaching Heat Stress",
        "Bathymetric Ridges", "Submarine Canyons", "River Plumes",
        "Estuary Mixing", "Thermohaline Circulation", "Ocean Eddies",
        "Internal Waves", "Sea Surface Winds", "Coastal Erosion",
        "Tsunami Propagation", "Ocean Carbon Uptake",
    ],
    "cryosphere": [
        "Arctic Sea Ice Extent", "Antarctic Sea Ice Extent", "Greenland Ice Loss",
        "Antarctic Ice Velocity", "Glacier Retreat", "Snow Cover",
        "Permafrost Temperature", "Ice Shelf Fractures", "Iceberg Drift",
        "Snow Water Equivalent", "Freeze Thaw Cycles", "Ice Sheet Elevation",
        "Firn Compaction", "Polar Albedo", "Sea Ice Age", "Sea Ice Thickness",
        "Mountain Snowpack", "Glacier Mass Balance", "Polar Amplification",
        "Ice Shelf Melting", "Melt Pond Evolution", "Seasonal Snowline",
        "River Ice Breakup", "Lake Ice Duration", "Arctic Coastal Erosion",
        "Polar Night Clouds", "Ice Core Climate Record", "Glacier Lake Outbursts",
        "Ice Sheet Grounding Lines", "Frozen Soil Carbon",
    ],
    "earth": [
        "Earthquake Waves", "Global Earthquake Catalog", "Plate Motion",
        "Volcanic Eruptions", "Lava Flow", "Topographic Relief", "River Deltas",
        "Watershed Networks", "Flood Inundation", "Landslide Susceptibility",
        "Soil Moisture", "Groundwater Depletion", "Land Subsidence",
        "Coastal Flooding", "Urban Heat Islands", "Night Lights",
        "Deforestation Frontiers", "Desertification", "Sand Dune Migration",
        "Sediment Transport", "River Discharge", "Mountain Uplift",
        "Geothermal Heat Flow", "Geomagnetic Field", "Gravity Anomalies",
        "Land Surface Temperature", "Crustal Deformation", "Surface Water Change",
        "Soil Erosion", "Fault Line Geometry",
    ],
    "biosphere": [
        "Forest Canopy Height", "Global Biomass", "Vegetation Seasons",
        "Animal Migration Routes", "Bird Population Trends", "Tree Cover Change",
        "Forest Fire Recovery", "Coral Reef Extent", "Mangrove Change",
        "Wetland Change", "Plant Phenology", "Pollinator Habitats",
        "Habitat Fragmentation", "Wildlife Corridors", "Species Richness",
        "Invasive Species Spread", "Reef Fish Diversity", "Seagrass Meadows",
        "Crop Health", "Agricultural Water Use", "Primary Productivity",
        "Forest Carbon Flux", "Savanna Greening", "Forest Drought Stress",
        "Peatland Carbon", "Urban Tree Canopy", "Harmful Algal Blooms",
        "Land Cover Transitions", "Ecosystem Resilience", "Leaf Area Index",
    ],
    "space": [
        "Solar Flares", "Aurora Oval", "Sunspot Cycle", "Solar Wind",
        "Coronal Mass Ejections", "Earth Radiation Belts", "Magnetosphere Dynamics",
        "Lunar Surface Relief", "Moon Phases", "Lunar Craters",
        "Mars Dust Storms", "Mars Topography", "Martian Polar Caps",
        "Jupiter Cloud Bands", "Saturn Rings", "Planetary Orbits",
        "Near Earth Asteroids", "Meteor Showers", "Exoplanet Transits",
        "Galaxy Redshift", "Star Formation Regions", "Cosmic Microwave Background",
        "Gravitational Waves", "Black Hole Accretion", "Comet Tails",
        "Space Station Orbit", "Satellite Constellations", "Space Weather Forecast",
        "Milky Way Star Density", "Hubble Expansion",
    ],
}

ENGINE = {"atmosphere": "globe", "ocean": "particles", "cryosphere": "globe",
          "earth": "terrain", "biosphere": "terrain", "space": "physics"}


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def build():
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else {"projects": []}
    status = {p["slug"]: p["status"] for p in existing["projects"]}
    projects = []
    # Keep the user's required first three projects in their specified order.
    ordered = [("atmosphere", "Saharan Dust"), ("atmosphere", "Atmospheric Rivers"),
               ("ocean", "Ocean Currents")]
    ordered += [(group, title) for group, topics in TOPICS.items() for title in topics
                if title not in {"Saharan Dust", "Atmospheric Rivers", "Ocean Currents"}]
    if len(ordered) != 180 or len({slug(t) for _, t in ordered}) != 180:
        raise ValueError("Backlog must contain exactly 180 unique ideas")
    for number, (category, title) in enumerate(ordered, 1):
        name = slug(title)
        projects.append({"number": number, "slug": name, "title": title,
                         "category": category,
                         "engine": "dust" if number == 1 else ENGINE[category],
                         "status": status.get(name, "backlog")})
    result = {"schema_version": 1, "target_count": 180,
              "candidate_limit_per_day": 3, "approved_buffer_target": 7,
              "projects": projects}
    OUT.write_bytes((json.dumps(result, indent=2) + "\n").encode("utf-8"))
    print(f"Saved {len(projects)} candidate ideas to {OUT}")


if __name__ == "__main__":
    build()
