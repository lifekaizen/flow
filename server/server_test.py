import json
import pprint
import unittest

from decimal import Decimal

from server import app, api, db
from database import Run, Protocol

from api.protocol import api as protocols
from api.run import api as runs


def create_app():
    app.config["TESTING"] = True
    app.config["AUTH_PROVIDER"] = "none"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/datalayer-test.db"
    api.add_namespace(protocols)
    api.add_namespace(runs)

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app()
        self.maxDiff = None

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_read_runs(self):
        # Load example runs.
        example_run_1 = Run()
        example_run_1.id = 6
        example_run_1.data = {
            "name": "Example Run 9",
            "notes": "Example notes!",
            "data_link": "https://s3.amazon.com/..."
        }
        db.session.add(example_run_1)

        response = self.client.get("/run")
        if response.json is None:
            pprint.pprint(response)
        self.assertEqual(response.json, [{
            "id": 6,
            "name": "Example Run 9",
            "notes": "Example notes!",
            "data_link": "https://s3.amazon.com/..."
        }])

    def test_create_and_get_run(self):
        # Load example protocols.
        example_protocol_1 = Protocol()
        example_protocol_1.id = 6
        example_protocol_1.data = {
            "name": "Example Protocol 9",
            "notes": "Example notes!"
        }
        db.session.add(example_protocol_1)

        data = {
            "protocol_id": 6,
            "name": "Test Run",
            "notes": "Test notes!",
            "data_link": "https://google.com/"
        }
        response = self.client.post(
            "/run",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"}
        )
        if response.json is None:
            pprint.pprint(response)
        self.assertEqual(response.json, {
            "id": response.json["id"],
            **data
        })
        response = self.client.get(f"/run/{response.json['id']}")
        if response.json is None:
            pprint.pprint(response)
        self.assertEqual(response.json, {
            "id": response.json["id"],
            **data
        })

    def test_read_protocols(self):
        # Load example protocols.
        example_protocol_1 = Protocol()
        example_protocol_1.id = 6
        example_protocol_1.data = {
            "name": "Example Protocol 9",
            "notes": "Example notes!"
        }
        db.session.add(example_protocol_1)

        response = self.client.get("/protocol")
        if response.json is None:
            pprint.pprint(response)
        self.assertEqual(response.json, [{
            "id": 6,
            "name": "Example Protocol 9",
            "notes": "Example notes!"
        }])

    def test_create_and_get_protocol(self):
        data = {
            "name": "Test Protocol",
            "notes": "Test notes!"
        }
        response = self.client.post(
            "/protocol",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"}
        )
        if response.json is None:
            pprint.pprint(response)
        self.assertEqual(response.json, {
            "id": response.json["id"],
            **data
        })
        response = self.client.get(f"/protocol/{response.json['id']}")
        if response.json is None:
            pprint.pprint(response)
        self.assertEqual(response.json, {
            "id": response.json["id"],
            **data
        })


if __name__ == "__main__":
    unittest.main()