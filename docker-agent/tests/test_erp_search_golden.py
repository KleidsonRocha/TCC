import json
import os

import pytest

from app.core.domain.pre_search import SearchCriteria
from scripts.eval.evaluate_erp_search import GOLDEN_PATH, evaluate


GOLDEN = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def test_erp_golden_has_valid_cases_and_audit_counterexamples():
    ids = [case["id"] for case in GOLDEN["cases"]]
    assert len(ids) == len(set(ids))
    for case in GOLDEN["cases"]:
        SearchCriteria(**case["criteria"])
        assert case["message"]
        assert case["fixture"] in GOLDEN["fixtures"]
    assert GOLDEN["cases"][0]["expected_ids"] == ["AUD-REAL"]
    assert {item["code"] for item in GOLDEN["fixtures"]["audit"]["candidates"]} == {
        "AUD-REAL", "AUD-GOLF", "AUD-CROSS", "AUD-CAP"
    }


@pytest.fixture(scope="module")
def postgres_results():
    if os.environ.get("ERP_SEARCH_TEST_POSTGRES") != "1":
        pytest.skip("Set ERP_SEARCH_TEST_POSTGRES=1 to run real PostgreSQL golden cases")
    return {(row["id"], row["backend"]): row for row in evaluate()}


@pytest.mark.parametrize("backend", ["contract", "snapshot"])
@pytest.mark.parametrize("case_id", [case["id"] for case in GOLDEN["cases"]])
def test_postgres_golden(case_id, backend, postgres_results):
    result = postgres_results[case_id, backend]
    assert result["passed"], result
