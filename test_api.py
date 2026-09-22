import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database
from main import app, translate_query
from fastapi.testclient import TestClient

def test_app():
    client = TestClient(app)

    print("--- 1. Testing GET /api/stats ---")
    r = client.get("/api/stats")
    assert r.status_code == 200, f"Stats failed: {r.text}"
    stats = r.json()
    print("Stats:", stats)
    assert stats['current']['total'] > 0, "No specials found in database"

    print("\n--- 2. Testing GET /api/specials (All) ---")
    r = client.get("/api/specials?limit=5")
    assert r.status_code == 200
    data = r.json()
    print(f"Total found: {data['total']}, sample items: {len(data['items'])}")
    for item in data['items'][:2]:
        print(f"  [{item['store']}] {item['title']} - {item['price_display']} (Save: ${item['save_amount']})")

    print("\n--- 3. Testing GET /api/specials with query & Chinese translation ---")
    translated = translate_query("洋芋片")
    print(f"Translated '洋芋片' -> '{translated}'")
    r = client.get("/api/specials?q=洋芋片")
    assert r.status_code == 200
    print(f"Specials for '洋芋片': {r.json()['total']}")

    print("\n--- 4. Testing GET /api/specials (Half Price only) ---")
    r = client.get("/api/specials?discount_only=true&limit=5")
    assert r.status_code == 200
    print(f"Half price specials: {r.json()['total']}")

    print("\n--- 5. Testing Shopping List CRUD ---")
    # Add item
    add_payload = {
        "store": "Coles",
        "title": "Arnott's Tim Tam 200g",
        "price": 2.50,
        "price_display": "$2.50 each",
        "quantity": 2,
        "save_amount": 2.50
    }
    r = client.post("/api/shopping-list", json=add_payload)
    assert r.status_code == 200
    new_id = r.json()['id']
    print(f"Added item ID: {new_id}")

    # Get shopping list
    r = client.get("/api/shopping-list")
    assert r.status_code == 200
    list_data = r.json()
    print(f"Shopping list total cost: ${list_data['total_cost']}, saved: ${list_data['total_saved']}")
    assert list_data['total_items'] >= 1

    # Toggle bought
    r = client.patch(f"/api/shopping-list/{new_id}", json={"is_bought": True})
    assert r.status_code == 200

    # Delete item
    r = client.delete(f"/api/shopping-list/{new_id}")
    assert r.status_code == 200
    print("Shopping list CRUD test passed!")

    print("\n--- 6. Testing Static Index HTML ---")
    r = client.get("/")
    assert r.status_code == 200
    assert "澳洲三大超市特價情報" in r.text
    print("Static HTML page successfully served!")

    print("\n ALL VERIFICATION TESTS PASSED SUCCESSFULLY! ")

if __name__ == '__main__':
    test_app()
