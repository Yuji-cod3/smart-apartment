from backend.app.demo import seed_demo
from backend.app.models.apartment import Apartment
from backend.app.models.device import Device
from backend.app.models.rent import RentCharge
from backend.app.models.user import User


def test_dashboard_page_and_assets_are_served(client):
    for path in ("/dashboard", "/dashboard/"):
        response = client.get(path)
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "/dashboard/assets/app.js" in response.text
        assert response.headers["cache-control"] == "no-store"
    for filename in ("app.js", "rent-countdown.mjs", "styles.css", "favicon.svg"):
        assert client.get(f"/dashboard/assets/{filename}").status_code == 200


def test_dashboard_does_not_expose_private_demo_files(client):
    for path in ("/.demo/credentials.json", "/dashboard/assets/.demo/credentials.json",
                 "/dashboard/assets/%2e%2e/%2e%2e/.demo/credentials.json"):
        assert client.get(path).status_code == 404


def test_demo_seed_is_repeatable_and_preserves_existing_records(db_session):
    assert seed_demo(db_session, "OnlyForLocalDemo123!") is True
    assert db_session.query(Apartment).count() == 6
    assert db_session.query(User).count() == 5
    assert db_session.query(Device).count() == 18
    assert db_session.query(RentCharge).count() == 8
    light = db_session.query(Device).filter_by(type="light").first()
    light.name = "Customized demo light"
    db_session.commit()
    assert seed_demo(db_session, "UnusedPassword123!") is False
    assert db_session.query(User).count() == 5
    assert db_session.get(Device, light.id).name == "Customized demo light"


def test_demo_seed_refuses_nonempty_application_database(db_session, tenant_user):
    assert seed_demo(db_session, "OnlyForLocalDemo123!") is False
    assert db_session.query(Apartment).count() == 0
    assert db_session.query(User).count() == 1
