import sqlite3
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import json
import os
from collections import defaultdict

print("=" * 50)
print("Graph Convolutional Network (GCN) - Embedding Generator")
print("=" * 50)

# 1. Load Data
conn = sqlite3.connect("data/finguard.db")
df = pd.read_sql_query("SELECT user_id, merchant, amount, is_fraud FROM transactions", conn)
conn.close()

# 2. Build Graph (Homogeneous for simplicity: Users and Merchants are nodes)
users = [f"U_{u}" for u in df["user_id"].unique()]
merchants = [f"M_{m}" for m in df["merchant"].unique()]
node_list = users + merchants
node2idx = {n: i for i, n in enumerate(node_list)}
num_nodes = len(node_list)

print(f"Graph nodes: {num_nodes} ({len(users)} users, {len(merchants)} merchants)")

# Node features: [degree, total_amount, avg_amount]
features = np.zeros((num_nodes, 3), dtype=np.float32)

# Build Adjacency Matrix and aggregate features
adj_indices = []
adj_values = []

# Self loops for GCN
for i in range(num_nodes):
    adj_indices.append([i, i])
    adj_values.append(1.0)

edge_stats = df.groupby(["user_id", "merchant"]).agg(
    count=("amount", "count"),
    total=("amount", "sum")
).reset_index()

for _, row in edge_stats.iterrows():
    u_idx = node2idx[f"U_{int(row['user_id'])}"]
    m_idx = node2idx[f"M_{row['merchant']}"]
    weight = row["count"]
    
    # Update node features
    features[u_idx, 0] += weight
    features[u_idx, 1] += row["total"]
    
    features[m_idx, 0] += weight
    features[m_idx, 1] += row["total"]
    
    # Add bidirectional edges
    # Weight can be 1.0 or normalized
    adj_indices.append([u_idx, m_idx])
    adj_indices.append([m_idx, u_idx])
    adj_values.append(1.0)
    adj_values.append(1.0)

# Calculate averages
features[:, 2] = np.where(features[:, 0] > 0, features[:, 1] / features[:, 0], 0)

# Normalize node features
means = features.mean(axis=0)
stds = features.std(axis=0) + 1e-9
features = (features - means) / stds

X_tensor = torch.tensor(features, dtype=torch.float32)

# Normalize Adjacency Matrix D^{-0.5} A D^{-0.5}
degree = defaultdict(float)
for pair, val in zip(adj_indices, adj_values):
    degree[pair[0]] += val

norm_indices = []
norm_values = []
for pair, val in zip(adj_indices, adj_values):
    u, v = pair
    w = val * (degree[u] ** -0.5) * (degree[v] ** -0.5)
    norm_indices.append([u, v])
    norm_values.append(w)

norm_indices = torch.tensor(norm_indices, dtype=torch.long).t()
norm_values = torch.tensor(norm_values, dtype=torch.float32)
A_sparse = torch.sparse_coo_tensor(norm_indices, norm_values, size=(num_nodes, num_nodes))

# 3. Define GCN Autoencoder
class GCNLayer(nn.Module):
    def __init__(self, in_dim, out_dim):
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim, bias=False)
        
    def forward(self, x, adj):
        support = self.linear(x)
        out = torch.sparse.mm(adj, support)
        return out

class GCNAutoencoder(nn.Module):
    def __init__(self, in_dim, hidden_dim, emb_dim):
        super().__init__()
        self.gcn1 = GCNLayer(in_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.gcn2 = GCNLayer(hidden_dim, emb_dim)
        
    def forward(self, x, adj):
        h = self.relu(self.gcn1(x, adj))
        z = self.gcn2(h, adj)
        return z

emb_dim = 8
model = GCNAutoencoder(in_dim=3, hidden_dim=16, emb_dim=emb_dim)
optimizer = optim.Adam(model.parameters(), lr=0.01)

# Edges for training
pos_edges = torch.tensor([[p[0], p[1]] for p in adj_indices if p[0] != p[1]], dtype=torch.long).t()
num_pos = pos_edges.shape[1]

print("🔄 Training GCN Autoencoder...")
model.train()
epochs = 200

# To stabilize training, manual seed
torch.manual_seed(42)
np.random.seed(42)

for epoch in range(epochs):
    optimizer.zero_grad()
    Z = model(X_tensor, A_sparse)
    
    pos_score = (Z[pos_edges[0]] * Z[pos_edges[1]]).sum(dim=1)
    
    # Negative sampling
    neg_u = torch.randint(0, num_nodes, (num_pos,))
    neg_v = torch.randint(0, num_nodes, (num_pos,))
    neg_score = (Z[neg_u] * Z[neg_v]).sum(dim=1)
    
    pos_loss = -torch.log(torch.sigmoid(pos_score) + 1e-15).mean()
    neg_loss = -torch.log(1 - torch.sigmoid(neg_score) + 1e-15).mean()
    loss = pos_loss + neg_loss
    
    loss.backward()
    optimizer.step()
    
    if (epoch+1) % 50 == 0:
        print(f"   Epoch {epoch+1}/{epochs} | Loss: {loss.item():.4f}")

model.eval()
with torch.no_grad():
    Z_final = model(X_tensor, A_sparse).numpy()

# 4. Save Embeddings
user_embeddings = {}
for n, idx in node2idx.items():
    if n.startswith("U_"):
        uid = int(n.split("_")[1])
        user_embeddings[uid] = Z_final[idx].tolist()

merchant_embeddings = {}
for n, idx in node2idx.items():
    if n.startswith("M_"):
        m_name = str(n.split("_", 1)[1])
        merchant_embeddings[m_name] = Z_final[idx].tolist()

os.makedirs("models", exist_ok=True)

# Save the trained standard GNN state dictionary too (for any realtime usage if needed)
torch.save(model.state_dict(), "models/gcn_model.pt")

with open("models/gnn_embeddings.json", "w") as f:
    json.dump({
        "user_embeddings": user_embeddings,
        "merchant_embeddings": merchant_embeddings,
        "emb_dim": emb_dim
    }, f, indent=2)

print("\n✅ Checkpoint Saved -> models/gcn_model.pt")
print("✅ Node Embeddings Generated -> models/gnn_embeddings.json")
print("=" * 50)
print("Part 1 Complete: Next, map these GNN embeddings directly into XGBoost training!")
