import inspect
import os
import database


def test_database_public_function_contracts_preserved():
    init_sig = inspect.signature(database.init_db)
    create_sig = inspect.signature(database.create_incident)
    update_sig = inspect.signature(database.update_incident)
    get_sig = inspect.signature(database.get_incident)
    list_sig = inspect.signature(database.get_all_incidents)
    add_msg_sig = inspect.signature(database.add_incident_message)
    msg_list_sig = inspect.signature(database.get_incident_messages)

    assert list(init_sig.parameters) == ["db_path", "seed_sample_data"]
    assert list(create_sig.parameters) == [
        "vehicle_type", "latitude", "longitude", "confidence",
        "rider_status", "language", "message", "status", "address",
        "incident_id", "timestamp", "db_path"
    ]
    assert list(update_sig.parameters) == ["incident_id", "db_path", "kwargs"]
    assert list(get_sig.parameters) == ["incident_id", "db_path"]
    assert list(list_sig.parameters) == ["limit", "db_path"]
    assert list(add_msg_sig.parameters) == ["incident_id", "sender", "original_text", "translated_text", "db_path"]
    assert list(msg_list_sig.parameters) == ["incident_id", "db_path"]


def test_database_backend_uses_database_url_environment_and_psycopg2():
    assert hasattr(database, "DATABASE_URL")
    assert hasattr(database, "get_connection")
    assert isinstance(database.DATABASE_URL, str)
    assert database.__name__ == "database"
