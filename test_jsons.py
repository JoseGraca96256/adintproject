from datetime import datetime, timezone
import json
import requests

# /d:/adi/adintproject/test_jsons.py

def jsonify_now(as_millis: bool = False) -> str:
    """
    Return a JSON string containing the current datetime.
    - as_millis=True: return epoch milliseconds instead of ISO string.
    """
    now = datetime.now()
    if as_millis:
        payload = {"now": int(now.timestamp() * 1000)}
        return json.dumps(payload)
    return json.dumps({"date": now.isoformat()})

if __name__ == "__main__":
    # examples
    print(jsonify_now())             # {"now": "2025-10-17T..."}
    print(jsonify_now(as_millis=True))  # {"now": 1700000000000}
    # Send to localhost:5000
    url = "http://localhost:5000/api/reserve/segredo"
    data = jsonify_now()
    response = requests.post(url, data=data, headers={"Content-Type": "application/json"})
    print(f"Response status: {response.status_code}")