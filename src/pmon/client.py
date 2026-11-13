"""A deliberately read-only wrapper around pueue's JSON interface."""
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
from .binaries import resolve_binary


class PueueError(RuntimeError):
    pass


@dataclass(frozen=True)
class Task:
    id: int
    status: str
    group: str
    label: str
    command: str
    path: str
    dependencies: tuple[int, ...]
    start: str | None = None
    end: str | None = None
    result: str | None = None


@dataclass(frozen=True)
class Snapshot:
    tasks: tuple[Task, ...]
    groups: dict
    observed_at: str


def parse_task(key, value):
    raw = value.get("status", "Unknown")
    details = {}
    result = None
    if isinstance(raw, dict):
        status = next(iter(raw), "Unknown")
        details = raw.get(status) or {}
        if not isinstance(details, dict):
            details = {}
        if status == "Done":
            outcome = details.get("result", "Unknown")
            result = outcome if isinstance(outcome, str) else json.dumps(outcome)
            status = "Success" if outcome == "Success" else "Failed"
    else:
        status = str(raw)
    return Task(id=int(key), status=status, group=value.get("group") or "default",
        label=value.get("label") or "", command=value.get("command") or "",
        path=value.get("path") or "", dependencies=tuple(value.get("dependencies") or ()),
        start=details.get("start"), end=details.get("end"), result=result)


class Client:
    def __init__(self, config, *, binary="pueue", profile=None, timeout=3.):
        self.config = Path(config).expanduser().resolve()
        if not self.config.is_file():
            raise PueueError(f"pueue 설정 파일 없음: {self.config}")
        self.binary = resolve_binary('pueue') if binary == 'pueue' else shutil.which(str(binary))
        if not self.binary:
            raise PueueError(f"pueue 실행 파일을 찾지 못했습니다: {binary}")
        self.profile = profile
        self.timeout = timeout

    def _query(self, operation, *args):
        if operation not in {"status", "log"}:
            raise PueueError("pmon은 status와 log만 조회합니다")
        command = [self.binary, "--config", str(self.config)]
        if self.profile:
            command += ["--profile", self.profile]
        command += [operation, "--json", *map(str, args)]
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired as exc:
            raise PueueError(f"pueue 응답 시간 초과 ({self.timeout:g}초)") from exc
        except OSError as exc:
            raise PueueError(f"pueue 실행 실패: {exc}") from exc
        if process.returncode:
            # Keep terminal error output concise; never dump status/env JSON.
            raise PueueError("pueue 조회 실패: daemon과 설정 경로를 확인하세요")
        try:
            value = json.loads(process.stdout)
            if not isinstance(value, dict):
                raise ValueError("Expected an object")
            return value
        except ValueError as exc:
            raise PueueError("pueue가 올바른 JSON을 반환하지 않았습니다") from exc

    def status(self, *, group=None):
        raw = self._query("status")
        try:
            tasks = tuple(sorted((parse_task(key, value) for key, value in raw.get("tasks", {}).items()),
                                 key=lambda task: task.id))
            groups = raw.get("groups", {})
            if group is not None:
                tasks = tuple(task for task in tasks if task.group == group)
                groups = {key: value for key, value in groups.items() if key == group}
            return Snapshot(tasks, groups, datetime.now().astimezone().isoformat())
        except (TypeError, ValueError, AttributeError) as exc:
            raise PueueError("지원하지 않는 pueue 상태 형식입니다") from exc

    def log(self, task_id, *, lines=12):
        if int(task_id) < 0 or not 1 <= lines <= 1000:
            raise ValueError("task_id >= 0, 1 <= lines <= 1000 이어야 합니다")
        data = self._query("log", "--lines", lines, int(task_id))
        entry = data.get(str(task_id))
        if not isinstance(entry, dict):
            raise PueueError(f"작업 {task_id}의 로그를 찾지 못했습니다")
        output = entry.get("output")
        return output if isinstance(output, str) else "(출력 없음)"
