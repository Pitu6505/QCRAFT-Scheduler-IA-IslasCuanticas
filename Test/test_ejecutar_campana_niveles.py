import asyncio
import unittest
from unittest.mock import patch

from ejecutar_campana_niveles import (
    SCENARIOS,
    completed_documents,
    matching_job_metrics,
    submit_scenario,
    wait_for_results,
)


class _ReadyResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return '[{"value": {"0": 12}}]'


class _ReadySession:
    def get(self, *args, **kwargs):
        return _ReadyResponse()


class _SubmissionResponse:
    def __init__(self, session, name):
        self.session = session
        self.name = name

    async def __aenter__(self):
        self.session.active += 1
        self.session.max_active = max(self.session.max_active, self.session.active)
        await asyncio.sleep(0.01)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.session.active -= 1

    def raise_for_status(self):
        return None

    async def text(self):
        return self.name


class _SubmissionSession:
    def __init__(self, *args, **kwargs):
        self.active = 0
        self.max_active = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return None

    def post(self, url, json):
        return _SubmissionResponse(self, json["url"])


class RunPlacementCampaignTests(unittest.TestCase):
    def test_decodes_scheduler_double_encoded_result(self):
        self.assertEqual(
            completed_documents('[{"value": {"0": 12}}]'),
            [{"value": {"0": 12}}],
        )

    def test_empty_results_are_still_pending(self):
        self.assertIsNone(completed_documents("[]"))

    def test_matches_each_submitted_id_to_one_batch_metric(self):
        records = [
            {"job_id": "job-a", "users": ["1", "2"]},
            {"job_id": "job-b", "users": ["3"]},
            {"job_id": "unrelated", "users": ["4"]},
        ]

        matched = matching_job_metrics(records, {"1", "2", "3"})

        self.assertEqual([record["job_id"] for record in matched], ["job-a", "job-b"])

    def test_missing_metrics_fail_instead_of_reporting_partial_success(self):
        with self.assertRaisesRegex(RuntimeError, "Faltan métricas"):
            matching_job_metrics([{"job_id": "job-a", "users": ["1"]}], {"1", "2"})

    def test_default_scenarios_keep_the_requested_order(self):
        self.assertEqual(
            [scenario[0] for scenario in SCENARIOS],
            ["nivel_3", "niveles_2_3", "niveles_1_2_3"],
        )

    def test_waiter_returns_only_after_scheduler_result_is_present(self):
        submitted = {"42": {"name": "test-circuit", "submitted_at": 0}}
        with patch("ejecutar_campana_niveles.time.monotonic", side_effect=[1, 2, 3]):
            result = wait_for_results(
                _ReadySession(),
                "http://scheduler",
                submitted,
                timeout_seconds=60,
                poll_seconds=1,
            )

        self.assertEqual(result["42"]["documents"], [{"value": {"0": 12}}])

    def test_scenario_submissions_launch_all_requests_concurrently(self):
        session = _SubmissionSession()
        circuits = [(f"circuit-{index}", str(index)) for index in range(6)]
        with patch(
            "ejecutar_campana_niveles.aiohttp.ClientSession",
            return_value=session,
        ), patch(
            "ejecutar_campana_niveles.aiohttp.TCPConnector",
            side_effect=lambda limit: self.assertEqual(limit, 0),
        ):
            submitted, errors = asyncio.run(
                submit_scenario(
                    "http://scheduler",
                    circuits,
                    "policy",
                    10000,
                )
            )

        self.assertEqual(errors, [])
        self.assertEqual(len(submitted), len(circuits))
        self.assertEqual(session.max_active, len(circuits))


if __name__ == "__main__":
    unittest.main()
