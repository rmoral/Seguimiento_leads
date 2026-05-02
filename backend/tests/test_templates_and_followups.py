from datetime import datetime, timedelta, timezone


def test_template_crud(auth_client):
    r = auth_client.post(
        "/templates",
        json={
            "name": "First touch",
            "subject": "Hola {name}",
            "body": "Hola {name}, te escribo desde {company}…",
            "variables": "name,company",
        },
    )
    assert r.status_code == 201
    tpl_id = r.json()["id"]

    r = auth_client.get("/templates")
    assert len(r.json()) == 1

    r = auth_client.patch(f"/templates/{tpl_id}", json={"subject": "Saludos {name}"})
    assert r.status_code == 200
    assert r.json()["subject"] == "Saludos {name}"

    r = auth_client.delete(f"/templates/{tpl_id}")
    assert r.status_code == 204


def test_followup_lifecycle(auth_client):
    lead_id = auth_client.post("/leads", json={"name": "Jane"}).json()["id"]
    when = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()

    r = auth_client.post(
        "/followups",
        json={"lead_id": lead_id, "scheduled_at": when, "notes": "Recordar"},
    )
    assert r.status_code == 201
    fu_id = r.json()["id"]

    r = auth_client.get("/followups")
    assert len(r.json()) == 1

    r = auth_client.patch(f"/followups/{fu_id}", json={"status": "done"})
    assert r.json()["status"] == "done"

    r = auth_client.delete(f"/followups/{fu_id}")
    assert r.status_code == 204
