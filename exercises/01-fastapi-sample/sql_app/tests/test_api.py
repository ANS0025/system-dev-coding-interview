from ..auth import create_token

def create_test_user(client, email="deadpool@example.com", password="chimichangas4life"):
    response = client.post(
        "/users/",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()

# Authentication Tests
def test_create_user(test_db, client):
    user = create_test_user(client)
    assert user["email"] == "deadpool@example.com"
    assert "id" in user
    assert user["is_active"] is True
    assert "items" in user
    assert "x_api_token" in user

def test_invalid_token(test_db, client):
    response = client.get("/users/", headers={"X-API-TOKEN": "invalid_token"})
    assert response.status_code == 401

def test_invalid_payload(test_db, client):
    token = create_token({"invalid": "payload"})
    response = client.get("/users/", headers={"X-API-TOKEN": token})
    assert response.status_code == 401

def test_non_existent_user_token(test_db, client):
    token = create_token({"sub": "nonexistent@example.com"})
    response = client.get("/users/", headers={"X-API-TOKEN": token})
    assert response.status_code == 404

def test_valid_token_and_user(test_db, client):
    user = create_test_user(client)
    response = client.get("/users/", headers={"X-API-TOKEN": user["x_api_token"]})
    assert response.status_code == 200

def test_authenticated_access(test_db, client):
    user = create_test_user(client)
    token = user["x_api_token"]
    
    # Test access to various endpoints
    endpoints = ["/users/", f"/users/{user['id']}", "/items/", "health-check", "me/items"]
    for endpoint in endpoints:
        response = client.get(endpoint, headers={"X-API-TOKEN": token})
        assert response.status_code == 200

    # Test creating an item
    response = client.post(
        f"/users/{user['id']}/items/",
        headers={"X-API-TOKEN": token},
        json={"title": "Test Item", "description": "This is a test item"}
    )
    assert response.status_code == 200

def test_unauthenticated_access(test_db, client):
    # Test access to various endpoints without authentication
    endpoints = ["/users/", "/users/1", "/items/"]
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code == 403

    # Test creating an item without authentication
    response = client.post("/users/1/items/", json={"title": "Test Item", "description": "This is a test item"})
    assert response.status_code == 403

# My Items Tests
def test_get_own_items_authenticated(test_db, client):
    user = create_test_user(client)

    # Create an item for the user
    client.post(
        f"/users/{user['id']}/items/",
        headers={"X-API-TOKEN": user["x_api_token"]},
        json={"title": "Test Item", "description": "Test Description"}
    )
    
    response = client.get("/me/items", headers={"X-API-TOKEN": user["x_api_token"]})
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Test Item"

# Delete User Tests
def test_delete_user(test_db, client):
    user = create_test_user(client)
    token = user["x_api_token"]
    response = client.delete(f"/users/{user['id']}", headers={"X-API-TOKEN": token})
    assert response.status_code == 200

def test_delete_non_existent_user(test_db, client):
    user = create_test_user(client)
    token = user["x_api_token"]
    response = client.delete("/users/999", headers={"X-API-TOKEN": token})
    assert response.status_code == 404

def test_delete_already_deleted_user(test_db, client):
    user = create_test_user(client, "user1@example.com", "password1")
    # Delete the user once
    client.delete(f"/users/{user['id']}", headers={"X-API-TOKEN": user["x_api_token"]})
    # Try to delete again
    response = client.delete(f"/users/{user['id']}", headers={"X-API-TOKEN": user["x_api_token"]})
    assert response.status_code == 401

def test_deleted_user_has_no_items(test_db, client):
    user1 = create_test_user(client, "user1@example.com", "password1")
    user2 = create_test_user(client, "user2@example.com", "password2")
    token1 = user1["x_api_token"]
    token2 = user2["x_api_token"]
    
    # Create an item for user2
    client.post(
        f"/users/{user2['id']}/items/",
        headers={"X-API-TOKEN": token2},
        json={"title": "User2 Item", "description": "Test"}
    )

    # Delete user2
    client.delete(f"/users/{user1['id']}", headers={"X-API-TOKEN": token2})
    
    # Check that user1 no longer exists
    client.get(f"/users/{user1['id']}/", headers={"X-API-TOKEN": token1})

    # Check that user1 has no items
    response = client.get(f"/users/{user1['id']}", headers={"X-API-TOKEN": token2})
    assert response.status_code == 200
    user = response.json()
    assert user["items"] == []

def test_items_transferred_to_oldest_active_user(test_db, client):
    # Create three users
    user1 = create_test_user(client, "user1@example.com", "password1")
    user3 = create_test_user(client, "user3@example.com", "password3")

    # Create an item for user3
    client.post(
        f"/users/{user3['id']}/items/",
        headers={"X-API-TOKEN": user3["x_api_token"]},
        json={"title": "User3 Item", "description": "Test Item"}
    )

    # Delete user3
    client.delete(f"/users/{user3['id']}", headers={"X-API-TOKEN": user3["x_api_token"]})

    # Check that user1 now has user3's item
    response = client.get("/me/items", headers={"X-API-TOKEN": user1["x_api_token"]})
    assert response.status_code == 200
    user1_items = response.json()
    assert len(user1_items) == 1
    assert user1_items[0]["title"] == "User3 Item"
