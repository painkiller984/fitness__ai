from app.repositories.local_memory import LocalProfileStore


def test_local_profile_store_remembers_and_deletes_profile() -> None:
    store = LocalProfileStore()

    saved = store.save("browser-1", {"name": "Антон", "weight_kg": 93})

    assert saved["name"] == "Антон"
    assert store.get("browser-1")["weight_kg"] == 93
    store.delete("browser-1")
    assert store.get("browser-1") is None
