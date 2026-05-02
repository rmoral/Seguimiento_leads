"""Template CRUD, validation, and tenant isolation."""


class TestTemplateCRUD:
    def test_create(self, auth_client):
        r = auth_client.post(
            "/templates",
            json={
                "name": "First touch",
                "subject": "Hola {name}",
                "body": "Hola {name}, te escribo desde {company}",
                "variables": "name,company",
            },
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "First touch"
        assert body["variables"] == "name,company"

    def test_list_orders_alphabetically(self, auth_client, make_template):
        make_template(name="Charlie")
        make_template(name="Alpha")
        make_template(name="Bravo")
        names = [t["name"] for t in auth_client.get("/templates").json()]
        assert names == ["Alpha", "Bravo", "Charlie"]

    def test_update_partial(self, auth_client, make_template):
        tpl = make_template()
        r = auth_client.patch(f"/templates/{tpl['id']}", json={"subject": "New subject"})
        assert r.status_code == 200
        assert r.json()["subject"] == "New subject"
        # Body preserved
        assert r.json()["body"] == tpl["body"]

    def test_delete(self, auth_client, make_template):
        tpl = make_template()
        r = auth_client.delete(f"/templates/{tpl['id']}")
        assert r.status_code == 204
        # Listing no longer contains it
        names = [t["id"] for t in auth_client.get("/templates").json()]
        assert tpl["id"] not in names


class TestTemplateValidation:
    def test_create_requires_name(self, auth_client):
        r = auth_client.post(
            "/templates", json={"subject": "S", "body": "B"}
        )
        assert r.status_code == 422

    def test_create_requires_subject(self, auth_client):
        r = auth_client.post("/templates", json={"name": "N", "body": "B"})
        assert r.status_code == 422

    def test_create_requires_body(self, auth_client):
        r = auth_client.post("/templates", json={"name": "N", "subject": "S"})
        assert r.status_code == 422


class TestTemplateAuth:
    def test_create_requires_auth(self, client):
        r = client.post("/templates", json={"name": "N", "subject": "S", "body": "B"})
        assert r.status_code == 401


class TestTemplateTenantIsolation:
    def test_b_cannot_see_a_templates(self, two_tenants):
        c = two_tenants["client"]
        c.post(
            "/templates",
            json={"name": "A-tpl", "subject": "x", "body": "y"},
            headers=two_tenants["hdr_a"],
        )
        r = c.get("/templates", headers=two_tenants["hdr_b"])
        assert r.json() == []

    def test_b_cannot_update_a_template(self, two_tenants):
        c = two_tenants["client"]
        tpl = c.post(
            "/templates",
            json={"name": "A-tpl", "subject": "x", "body": "y"},
            headers=two_tenants["hdr_a"],
        ).json()
        r = c.patch(
            f"/templates/{tpl['id']}",
            json={"subject": "hacked"},
            headers=two_tenants["hdr_b"],
        )
        assert r.status_code == 404

    def test_b_cannot_delete_a_template(self, two_tenants):
        c = two_tenants["client"]
        tpl = c.post(
            "/templates",
            json={"name": "A-tpl", "subject": "x", "body": "y"},
            headers=two_tenants["hdr_a"],
        ).json()
        r = c.delete(f"/templates/{tpl['id']}", headers=two_tenants["hdr_b"])
        assert r.status_code == 404
