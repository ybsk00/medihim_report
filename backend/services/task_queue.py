"""Cloud Tasks 큐 서비스 — 파이프라인을 '요청 처리 중'으로 실행하기 위한 자기 호출 태스크 발행

배경: Cloud Run(min-instances=0, request-based CPU)은 HTTP 응답을 보낸 뒤의
백그라운드 작업을 "요청 없음"으로 간주해 CPU를 제한하고 인스턴스를 언제든 회수한다
(2026-07-18 seiji 상담 2건이 파이프라인 도중 SIGTERM으로 유실된 원인).

Cloud Tasks가 내부 엔드포인트(/api/webhook/internal/process)를 HTTP로 호출하면
파이프라인이 요청 수명 안에서 실행되므로:
  - 처리 중에는 CPU가 정상 할당되고 인스턴스가 회수되지 않는다
  - 인스턴스가 죽으면 Cloud Tasks가 태스크를 자동 재시도한다
콜드스타트 비용 정책(min-instances=0, 유휴 시 0원)은 그대로 유지된다.

CLOUD_TASKS_ENABLED 미설정(로컬 개발) 또는 발행 실패 시 False를 반환하고,
호출부가 기존 BackgroundTasks 방식으로 폴백한다.
"""

import asyncio
import json
import logging

from config import (
    CLOUD_TASKS_ENABLED,
    CLOUD_TASKS_LOCATION,
    CLOUD_TASKS_QUEUE,
    GCP_PROJECT,
    INTERNAL_TASK_SECRET,
    SELF_URL,
)

logger = logging.getLogger(__name__)

# Cloud Tasks HTTP 태스크 최대 응답 대기 시간 (서비스 상한 30분)
_DISPATCH_DEADLINE_SECONDS = 1800


def _enqueue_sync(payload: dict) -> str:
    from google.cloud import tasks_v2
    from google.protobuf import duration_pb2

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(GCP_PROJECT, CLOUD_TASKS_LOCATION, CLOUD_TASKS_QUEUE)
    task = tasks_v2.Task(
        http_request=tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=f"{SELF_URL}/api/webhook/internal/process",
            headers={
                "Content-Type": "application/json",
                "X-Internal-Auth": INTERNAL_TASK_SECRET,
            },
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ),
        dispatch_deadline=duration_pb2.Duration(seconds=_DISPATCH_DEADLINE_SECONDS),
    )
    response = client.create_task(request={"parent": parent, "task": task})
    return response.name


async def enqueue_pipeline_task(consultation_id: str, webhook_data: dict | None = None) -> bool:
    """파이프라인 실행 태스크 발행. 성공 시 True, 비활성/실패 시 False(호출부 폴백)."""
    if not (CLOUD_TASKS_ENABLED and SELF_URL and GCP_PROJECT):
        return False

    payload = {"consultation_id": consultation_id, "webhook_data": webhook_data}
    try:
        task_name = await asyncio.to_thread(_enqueue_sync, payload)
        logger.info(
            f"[TaskQueue] Enqueued pipeline task: consultation={consultation_id}, "
            f"task={task_name.rsplit('/', 1)[-1]}"
        )
        return True
    except Exception as e:
        logger.error(
            f"[TaskQueue] Enqueue failed (BackgroundTasks로 폴백): "
            f"consultation={consultation_id}, error={e}"
        )
        return False
