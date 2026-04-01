import traceback
from fastapi.testclient import TestClient
try:
    from api import app
    client = TestClient(app, raise_server_exceptions=True)
    res = client.post('/score', json={'user_id': 1, 'amount': 500, 'timestamp': '2023-01-01T14:00:00Z', 'location': 'Mumbai', 'merchant': 'Amazon', 'time_gap_override': -1})
    print(res.json())
except Exception as e:
    traceback.print_exc()
