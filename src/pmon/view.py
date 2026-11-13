"""Terminal rendering for pueue task snapshots."""
from collections import Counter
from datetime import datetime
import re
import unicodedata


ESCAPES = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]|\x1b.")


def clean(value):
    return "".join(c for c in ESCAPES.sub("", str(value)) if c >= " " and c != "\x7f")


def cell(value, width):
    text = clean(value)
    size = 0
    output = ""
    for char in text:
        n = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in "WF" else 1)
        if size+n > width:
            break
        size += n
        output += char
    return output+" "*max(0, width-size)


def elapsed(task):
    if not task.start:
        return "-"
    try:
        start = datetime.fromisoformat(task.start)
        end = datetime.fromisoformat(task.end) if task.end else datetime.now().astimezone()
        seconds = max(0, int((end-start).total_seconds()))
        h, rest = divmod(seconds, 3600)
        m, s = divmod(rest, 60)
        return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"
    except (ValueError, TypeError):
        return "-"


def render(snapshot, *, width=100, height=30, log_text=None, log_id=None, error=None):
    width = max(40, width)
    counts = Counter(task.status for task in snapshot.tasks)
    lines = ["pmon  /  pueue live monitor", clean(snapshot.observed_at),
        "  ".join(f"{name}: {counts[name]}" for name in ("Running", "Queued", "Paused", "Success", "Failed")), ""]
    groups = []
    for name, value in snapshot.groups.items():
        groups.append(f"{name} ({value.get('status', '?')}, parallel={value.get('parallel_tasks', '?')})")
    lines += ["Groups: "+", ".join(groups), ""]
    available = max(1, height-12-(8 if log_text is not None else 0))
    # Keep running/waiting work visible when a queue has a long history.
    active = [t for t in snapshot.tasks if t.status not in ("Success", "Failed")]
    finished = [t for t in snapshot.tasks if t.status in ("Success", "Failed")]
    tasks = active+finished[-max(0, available-len(active)):] if available > len(active) else active
    tasks = tasks[:available]
    columns = [("ID", 5), ("STATE", 12), ("GROUP", 15), ("ELAPSED", 10)]
    compact = width < 72
    if compact:
        columns = [("ID", 4), ("STATE", 10)]
    label_width = max(8, width-sum(n+1 for _, n in columns))
    lines.append(" ".join(cell(name, n) for name, n in columns)+" "+cell("LABEL / COMMAND", label_width))
    lines.append("─"*width)
    for task in tasks:
        values = [task.id, task.status] if compact else [task.id, task.status, task.group, elapsed(task)]
        label = task.label or task.command
        if task.dependencies:
            label += " ← "+",".join(map(str, task.dependencies))
        lines.append(" ".join(cell(v, n) for v, (_, n) in zip(values, columns))+" "+cell(label, label_width))
        if task.status == "Failed" and task.result:
            lines.append("      "+clean(task.result))
    if len(tasks) < len(snapshot.tasks):
        lines.append(f"… {len(snapshot.tasks)-len(tasks)}개 생략 (전체 목록: --once 또는 --json)")
    if not snapshot.tasks:
        lines.append("등록된 작업 없음")
    if log_text is not None:
        lines += ["", f"Log: task {log_id}", "─"*width]
        lines += [clean(line) for line in log_text.splitlines()[-6:]] or ["(출력 없음)"]
    if error:
        lines += ["", "연결 오류 · 마지막 조회 화면 유지: "+clean(error)]
    lines += ["", "q / Ctrl+C 종료 · r 즉시 갱신 · 읽기 전용 (작업은 계속 실행)"]
    return "\n".join(cell(line, width).rstrip() for line in lines)
