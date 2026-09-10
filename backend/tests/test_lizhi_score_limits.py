"""砺质评分不再受通用5分上限影响的回归测试。"""

import asyncio

import pytest
from fastapi import HTTPException

from api import scoring as scoring_api
from core import audit
from core.llm_client import QwenClient
from models.models import InspectionRecord, InspectionTask, ScoringResult


def test_lizhi_ai_result_uses_item_max_score_instead_of_five():
    items = [{
        "item_id": "安防-001",
        "item_name": "消防通道杂物率",
        "max_score": 20,
    }]

    matched = QwenClient._match_ai_results(
        [{"item_id": "安防-001", "score": 14, "scoring_basis": "按规则计算"}],
        items,
        "安防楼道净通行",
    )
    over_max = QwenClient._match_ai_results(
        [{"item_id": "安防-001", "score": 26}],
        items,
        "安防楼道净通行",
    )

    assert matched[0]["score"] == 14
    assert over_max[0]["score"] == 20


def test_non_lizhi_ai_result_keeps_five_point_limit():
    matched = QwenClient._match_ai_results(
        [{"item_id": "安全-001", "score": 8}],
        [{"item_id": "安全-001", "item_name": "门岗管理"}],
        "安全管理",
    )

    assert matched[0]["score"] == 5


def _create_lizhi_scoring_result(db_session, test_project):
    task = InspectionTask(
        task_id="Q-LIZHI-SCORE-LIMIT",
        project_id=test_project.id,
        check_date="2026-08-03",
        status="completed",
        standard_type="lizhi",
    )
    record = InspectionRecord(
        record_id="REC-LIZHI-SCORE-LIMIT",
        task_id=task.task_id,
        project_id=test_project.id,
        module_name="安防楼道净通行",
        check_date="2026-08-03",
        status="completed",
    )
    result = ScoringResult(
        scoring_id="SCR-LIZHI-SCORE-LIMIT",
        record_id=record.record_id,
        module_name=record.module_name,
        item_id="安防-001",
        item_name="消防通道杂物率",
        score=5,
        weight=0,
        weighted_score=5,
        scoring_basis="AI原始评分",
        is_skipped=False,
    )
    db_session.add_all([task, record, result])
    db_session.commit()
    return result


def test_lizhi_manual_edit_accepts_score_above_five(
    db_session, test_project, admin_user, monkeypatch
):
    result = _create_lizhi_scoring_result(db_session, test_project)
    monkeypatch.setattr(scoring_api, "_get_item_max_score", lambda *_: 20.0)
    monkeypatch.setattr(scoring_api, "_compute_and_save_total_score", lambda *_: None)
    monkeypatch.setattr(audit, "log_action", lambda *args, **kwargs: None)

    response = asyncio.run(
        scoring_api.edit_score(
            result.scoring_id,
            scoring_api.ScoreEditRequest(score=14, scoring_basis="人工按砺质规则复核"),
            db_session,
            admin_user,
        )
    )
    db_session.refresh(result)

    assert response["new_score"] == 14
    assert float(result.score) == 14
    assert float(result.weighted_score) == 14


def test_lizhi_manual_edit_still_rejects_score_above_item_max(
    db_session, test_project, admin_user, monkeypatch
):
    result = _create_lizhi_scoring_result(db_session, test_project)
    monkeypatch.setattr(scoring_api, "_get_item_max_score", lambda *_: 20.0)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            scoring_api.edit_score(
                result.scoring_id,
                scoring_api.ScoreEditRequest(score=20.5),
                db_session,
                admin_user,
            )
        )

    assert exc_info.value.status_code == 400
    assert "0-20" in exc_info.value.detail
