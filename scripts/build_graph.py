# scripts/build_graph.py
# Builds transaction graph from database
# Nodes = users + merchants
# Edges = transactions between them

import sqlite3
import pandas as pd
import networkx as nx
import json
import os

conn = pd.read_sql_query("SELECT * FROM transactions", 
                          sqlite3.connect("data/finguard.db"))
conn2 = pd.read_sql_query("SELECT * FROM users",
                           sqlite3.connect("data/finguard.db"))

df       = conn
users_df = conn2

# Build directed graph
G = nx.DiGraph()

# Add user nodes
user_info = {
    1: {"name": "Aman",  "persona": "Student",     "color": "#58a6ff"},
    2: {"name": "Riya",  "persona": "NightOwl",    "color": "#bc8cff"},
    3: {"name": "Kabir", "persona": "VIP",         "color": "#ffa657"},
}

for uid, info in user_info.items():
    G.add_node(
        f"user_{uid}",
        label=info["name"],
        type="user",
        persona=info["persona"],
        color=info["color"],
        size=30
    )

# Add merchant nodes + edges
merchant_colors = {
    "Amazon":        "#f0883e",
    "Swiggy":        "#3fb950",
    "Zomato":        "#f85149",
    "Steam":         "#58a6ff",
    "EpicGames":     "#bc8cff",
    "LuxuryMall":    "#ffa657",
    "Airline":       "#d29922",
    "Hotel":         "#58a6ff",
    "BookStore":     "#3fb950",
    "UnknownMerchant": "#f85149",
}

# Count transactions per user-merchant pair
edge_counts = df.groupby(["user_id", "merchant"]).agg(
    count=("amount", "count"),
    total=("amount", "sum"),
    fraud_count=("is_fraud", "sum")
).reset_index()

for _, row in edge_counts.iterrows():
    merchant = row["merchant"]
    uid      = int(row["user_id"])
    count    = int(row["count"])
    total    = float(row["total"])
    is_fraud = int(row["fraud_count"]) > 0

    # Add merchant node if not exists
    if merchant not in G.nodes:
        G.add_node(
            merchant,
            label=merchant,
            type="merchant",
            color=merchant_colors.get(merchant, "#8b949e"),
            size=15
        )

    # Add edge — user → merchant
    G.add_edge(
        f"user_{uid}",
        merchant,
        weight=count,
        total=round(total, 2),
        has_fraud=is_fraud,
        color="#f85149" if is_fraud else "#30363d"
    )

# ── Network Analytics ──
# 1. Betweenness Centrality
centrality = nx.betweenness_centrality(G)
for node in G.nodes():
    G.nodes[node]["centrality"] = round(centrality.get(node, 0.0), 4)

# 2. Fraud Rings
fraud_edges_list = [(u, v) for u, v, d in G.edges(data=True) if d.get("has_fraud")]
fraud_G = nx.Graph()
fraud_G.add_edges_from(fraud_edges_list)
rings = [list(c) for c in nx.connected_components(fraud_G) if len(c) >= 2]
ring_nodes = {n for r in rings for n in r}
for node in G.nodes():
    G.nodes[node]["in_fraud_ring"] = node in ring_nodes

# Save graph stats as JSON for dashboard
stats = {
    "nodes":     G.number_of_nodes(),
    "edges":     G.number_of_edges(),
    "users":     3,
    "merchants": G.number_of_nodes() - 3,
    "fraud_edges": sum(1 for _, _, d in G.edges(data=True) if d.get("has_fraud")),
    "fraud_rings": len(rings),
    "largest_ring": max((len(r) for r in rings if r), default=0)
}

os.makedirs("models", exist_ok=True)
with open("models/graph_stats.json", "w") as f:
    json.dump(stats, f)

print(f"✅ Graph built: {stats['nodes']} nodes, {stats['edges']} edges")
print(f"   Fraud edges: {stats['fraud_edges']}")

# Save edge list for dashboard rendering
edges = []
for u, v, d in G.edges(data=True):
    edges.append({
        "from":      u,
        "to":        v,
        "weight":    d["weight"],
        "total":     d["total"],
        "has_fraud": d["has_fraud"],
        "color":     d["color"]
    })

nodes = []
for node, d in G.nodes(data=True):
    nodes.append({
        "id":      node,
        "label":   d.get("label", node),
        "type":    d.get("type", "merchant"),
        "color":   d.get("color", "#8b949e"),
        "size":    d.get("size", 15),
        "persona": d.get("persona", ""),
        "centrality": d.get("centrality", 0.0),
        "in_fraud_ring": d.get("in_fraud_ring", False)
    })

graph_data = {"nodes": nodes, "edges": edges, "stats": stats}
with open("models/graph_data.json", "w") as f:
    json.dump(graph_data, f, indent=2)

print("✅ Graph data saved → models/graph_data.json")