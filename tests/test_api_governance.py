"""
Integration tests over the API.

The unit tests prove the rules are correct. These prove the rules are actually
*reachable* — that the HTTP layer enforces them rather than merely importing
the module that defines them. Correct logic behind a route that never calls it
is the failure mode worth guarding against.
"""

from tests.conftest import API


class TestRegistration:
    def test_new_models_start_in_pilot(self, register):
        model = register()
        assert model["stage"] == "pilot"
        assert model["governance_score"] is None

    def test_registration_writes_its_own_audit_entry(self, client, register):
        model = register()
        history = client.get(f"{API}/models/{model['id']}/history").json()
        assert len(history) == 1
        assert history[0]["from_stage"] is None
        assert history[0]["to_stage"] == "pilot"

    def test_duplicate_version_is_rejected(self, client, register):
        """
        Regression test.

        Nothing enforced uniqueness on (name, version), so re-running a
        registration script silently created a second model with the same
        identity and a different ID. Two rows claiming to be v1.0.0 leave the
        registry unable to answer which one is live, and each accumulates its
        own separate approval history. For a system whose entire job is knowing
        what models exist, this was the worst possible bug to have.
        """
        register(name="dupe-check", version="v1.0.0")

        resp = client.post(
            f"{API}/models",
            json={
                "name": "dupe-check",
                "version": "v1.0.0",
                "model_type": "traditional_ml",
                "use_case": "Trying again",
                "owner": "someone-else",
            },
        )
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"]

        # And only one survives.
        names = [m["name"] for m in client.get(f"{API}/models").json()]
        assert names.count("dupe-check") == 1

    def test_same_name_different_version_is_allowed(self, client, register):
        """Versioning is the whole point — v0.9.0 and v1.0.0 of one model must
        coexist, each with its own stage and history."""
        register(name="versioned", version="v0.9.0")
        register(name="versioned", version="v1.0.0")

        matches = [m for m in client.get(f"{API}/models").json() if m["name"] == "versioned"]
        assert len(matches) == 2
        assert {m["version"] for m in matches} == {"v0.9.0", "v1.0.0"}


class TestPromotionGate:
    def test_low_scoring_high_risk_model_is_blocked(self, register, score, promote):
        model = register(risk_tier="high")
        score(model["id"], 6.0)
        promote(model["id"], "review")

        resp = promote(model["id"], "production", by="risk-committee")
        assert resp.status_code == 403
        # The refusal has to explain itself; a bare 403 is useless to whoever
        # has to fix it.
        assert "8.5" in resp.json()["detail"]

    def test_well_scoring_high_risk_model_is_allowed(self, register, score, promote):
        model = register(risk_tier="high")
        score(model["id"], 9.0)
        promote(model["id"], "review")

        resp = promote(model["id"], "production", by="risk-committee")
        assert resp.status_code == 200
        assert resp.json()["stage"] == "production"

    def test_same_score_passes_medium_and_fails_high(self, register, score, promote):
        """The tiering doing real work: identical models, identical scores,
        different answers because the blast radius differs."""
        for tier, expected in (("medium", 200), ("high", 403)):
            model = register(name=f"tier-{tier}", risk_tier=tier)
            score(model["id"], 8.0)
            promote(model["id"], "review")
            assert promote(model["id"], "production").status_code == expected

    def test_skipping_review_is_a_400_not_a_403(self, register, score, promote):
        """Two independent defences that must stay distinguishable: 400 means
        the path is illegal, 403 means the model isn't good enough. Collapsing
        them would hide which rule actually fired."""
        model = register(risk_tier="low")
        score(model["id"], 10.0)

        resp = promote(model["id"], "production")
        assert resp.status_code == 400
        assert "Cannot move model" in resp.json()["detail"]

    def test_a_blocked_promotion_leaves_no_trace(self, client, register, score, promote):
        """A refused approval is not an event. If failed attempts appeared in
        the audit trail it would be impossible to tell what was approved from
        what was merely tried."""
        model = register(risk_tier="high")
        score(model["id"], 5.0)
        promote(model["id"], "review")
        promote(model["id"], "production")

        history = client.get(f"{API}/models/{model['id']}/history").json()
        assert [e["to_stage"] for e in history] == ["pilot", "review"]


class TestKillSwitch:
    def test_deactivates_from_production_and_is_flagged(
        self, client, register, score, promote
    ):
        model = register(risk_tier="low")
        score(model["id"], 9.0)
        promote(model["id"], "review")
        promote(model["id"], "production")

        resp = client.post(
            f"{API}/models/{model['id']}/kill-switch",
            params={"reason": "Producing invalid scores", "triggered_by": "ops-lead"},
        )
        assert resp.status_code == 200
        assert resp.json()["stage"] == "deprecated"

        last = client.get(f"{API}/models/{model['id']}/history").json()[-1]
        assert last["is_emergency"] is True
        assert "EMERGENCY" in last["comment"]

    def test_works_straight_from_pilot(self, client, register):
        """An emergency stop must not require walking the model through the
        normal stages first — that's the entire reason it bypasses the
        transition map."""
        model = register()
        resp = client.post(
            f"{API}/models/{model['id']}/kill-switch",
            params={"reason": "Leaking PII in logs", "triggered_by": "security"},
        )
        assert resp.status_code == 200
        assert resp.json()["stage"] == "deprecated"

    def test_refuses_a_blank_reason(self, client, register):
        model = register()
        resp = client.post(
            f"{API}/models/{model['id']}/kill-switch",
            params={"reason": "   ", "triggered_by": "someone"},
        )
        assert resp.status_code == 400

    def test_routine_approvals_are_not_flagged_as_emergencies(
        self, client, register, promote
    ):
        model = register()
        promote(model["id"], "review")
        history = client.get(f"{API}/models/{model['id']}/history").json()
        assert all(e["is_emergency"] is False for e in history)


class TestAuditTrail:
    def test_records_every_transition_in_order(self, client, register, score, promote):
        model = register(risk_tier="low")
        score(model["id"], 9.0)
        promote(model["id"], "review", by="s.rao")
        promote(model["id"], "production", by="risk-committee")
        promote(model["id"], "review", by="drift-monitor-service")

        history = client.get(f"{API}/models/{model['id']}/history").json()
        assert [e["to_stage"] for e in history] == [
            "pilot", "review", "production", "review",
        ]
        assert history[-1]["approved_by"] == "drift-monitor-service"

    def test_automated_actors_use_the_same_path_as_humans(
        self, client, register, score, promote
    ):
        """The design claim under test: a monitor demoting a model produces the
        same kind of record as a person doing it, with no privileged route."""
        model = register(risk_tier="low")
        score(model["id"], 9.0)
        promote(model["id"], "review")
        promote(model["id"], "production")

        resp = promote(
            model["id"], "review", by="drift-monitor-service", comment="Auto-flagged"
        )
        assert resp.status_code == 200

        last = client.get(f"{API}/models/{model['id']}/history").json()[-1]
        assert last["is_emergency"] is False
        assert last["approved_by"] == "drift-monitor-service"


class TestMetrics:
    def test_logs_and_returns_in_chronological_order(self, client, register):
        model = register()
        for i, value in enumerate([0.90, 0.88, 0.79]):
            resp = client.post(
                f"{API}/models/{model['id']}/metrics",
                json={
                    "metric_name": "accuracy",
                    "metric_value": value,
                    "recorded_at": f"2026-0{i + 1}-15T00:00:00",
                },
            )
            assert resp.status_code == 201

        metrics = client.get(f"{API}/models/{model['id']}/metrics").json()
        assert [m["metric_value"] for m in metrics] == [0.90, 0.88, 0.79]

    def test_backfilled_timestamp_is_honoured(self, client, register):
        """Backfilling a measurement is legitimate — the number genuinely
        describes that date. Backdating an approval is not, and the API offers
        no way to do it."""
        model = register()
        client.post(
            f"{API}/models/{model['id']}/metrics",
            json={
                "metric_name": "auc",
                "metric_value": 0.71,
                "recorded_at": "2020-03-31T00:00:00",
            },
        )
        assert client.get(f"{API}/models/{model['id']}/metrics").json()[0][
            "recorded_at"
        ].startswith("2020-03-31")

    def test_approval_requests_cannot_carry_a_timestamp(self, client, register, promote):
        """An audit trail whose dates can be chosen isn't an audit trail. The
        field is ignored rather than accepted, so a caller can't quietly
        rewrite when a decision was taken."""
        model = register()
        resp = client.post(
            f"{API}/models/{model['id']}/approve",
            json={
                "to_stage": "review",
                "approved_by": "tester",
                "created_at": "1999-01-01T00:00:00",
            },
        )
        assert resp.status_code == 200
        assert not client.get(f"{API}/models/{model['id']}/history").json()[-1][
            "created_at"
        ].startswith("1999")

    def test_filtering_by_name(self, client, register):
        model = register()
        for name in ("accuracy", "accuracy", "drift_share"):
            client.post(
                f"{API}/models/{model['id']}/metrics",
                json={"metric_name": name, "metric_value": 0.5},
            )
        filtered = client.get(
            f"{API}/models/{model['id']}/metrics", params={"metric_name": "accuracy"}
        ).json()
        assert len(filtered) == 2


class TestLineage:
    def test_create_is_idempotent(self, client, register):
        """Registration scripts get re-run. Re-posting the same source has to
        be safe, or the register fills with duplicates every time someone
        repeats a step."""
        model = register()
        payload = {
            "source_table": "gst_returns",
            "features_used": ["turnover", "filing_delay"],
            "notes": "Monthly filings",
        }
        first = client.post(f"{API}/models/{model['id']}/lineage", json=payload)
        second = client.post(f"{API}/models/{model['id']}/lineage", json=payload)

        assert first.status_code == 201
        assert second.status_code == 200
        assert len(client.get(f"{API}/models/{model['id']}/lineage").json()) == 1

    def test_portfolio_export_spans_every_model(self, client, register):
        for name in ("model-a", "model-b"):
            model = register(name=name)
            client.post(
                f"{API}/models/{model['id']}/lineage",
                json={"source_table": "shared_table", "features_used": ["x"]},
            )

        rows = client.get(f"{API}/lineage").json()
        assert len(rows) == 2
        # The reverse lookup this endpoint exists for: which models touch a
        # given source?
        assert {r["model_name"] for r in rows if r["source_table"] == "shared_table"} == {
            "model-a",
            "model-b",
        }


class TestMisc:
    def test_health_reports_the_database_backend(self, client):
        """A deployment silently falling back to ephemeral SQLite looks fine
        until a redeploy erases everything, so the backend is reported rather
        than assumed."""
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert "database" in body and "persistent" in body

    def test_unknown_model_is_a_404(self, client):
        assert client.get(f"{API}/models/does-not-exist").status_code == 404

    def test_scores_are_bounded(self, client, register):
        model = register()
        assert (
            client.patch(
                f"{API}/models/{model['id']}/scores", json={"efficiency_score": 11.0}
            ).status_code
            == 422
        )

    def test_governance_score_averages_only_what_is_scored(self, client, register):
        """A partially scored model should not be penalised as though the
        missing dimensions were zero — but it still can't reach production,
        which the workflow tests cover."""
        model = register()
        body = client.patch(
            f"{API}/models/{model['id']}/scores",
            json={"efficiency_score": 8.0, "adoption_score": 6.0},
        ).json()
        assert body["governance_score"] == 7.0
