import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import select
import shutil
import sys
import time
import tomllib

from . import __version__
from .client import Client, PueueError
from .view import render


@contextmanager
def terminal_keys(enabled):
    original = None
    try:
        if enabled and sys.stdin.isatty() and sys.platform != "win32":
            import termios
            import tty
            original = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
        yield original is not None
    finally:
        if original is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, original)


def settings(parser, args):
    path = Path(args.settings).expanduser().resolve() if args.settings else Path.cwd()/"pmon.toml"
    defaults = {}
    if path.is_file():
        try:
            defaults = tomllib.loads(path.read_text()).get("connection", {})
        except (ValueError, OSError) as exc:
            parser.error(f"설정 파일 읽기 실패: {exc}")
    elif args.settings:
        parser.error(f"설정 파일 없음: {path}")
    config = args.config or defaults.get("config")
    if not config:
        local = Path.cwd()/".pueue/config.yml"
        if local.is_file():
            config = local
        else:
            parser.error("--config로 기존 pueue 설정을 지정하거나 pmon.toml을 작성하세요. 홈 폴더 설정은 자동 생성하지 않습니다.")
    else:
        config = Path(config).expanduser()
        if not config.is_absolute():
            config = (Path.cwd() if args.config else path.parent)/config
    return config, args.group if args.group is not None else defaults.get("group"), args.profile or defaults.get("profile")


def main(argv=None):
    parser = argparse.ArgumentParser(description="pueue queue 실시간 읽기 전용 모니터")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--config", help="기존 pueue config.yml 경로")
    parser.add_argument("--settings", help="pmon.toml 경로 (기본: 현재 폴더)")
    parser.add_argument("--group", help="그룹 필터 (기본: 전체)")
    parser.add_argument("--profile", help="pueue profile")
    parser.add_argument("--binary", default="pueue", help="pueue 실행 파일")
    parser.add_argument("--interval", type=float, default=2., help="갱신 주기, 초 (기본: 2)")
    parser.add_argument("--log", nargs="?", const="auto", help="작업 ID의 로그 표시; ID 생략 시 실행 중인 첫 작업")
    parser.add_argument("--once", action="store_true", help="한 번 출력 후 종료")
    parser.add_argument("--json", action="store_true", help="환경변수를 제외한 상태 JSON 한 번 출력")
    args = parser.parse_args(argv)
    if not .5 <= args.interval <= 3600:
        parser.error("--interval은 0.5~3600초여야 합니다")
    if args.log is not None and args.log != "auto" and not args.log.isdecimal():
        parser.error("--log에는 0 이상의 작업 ID를 사용하세요")
    config, group, profile = settings(parser, args)
    try:
        client = Client(config, binary=args.binary, profile=profile)
    except PueueError as exc:
        parser.error(str(exc))
    live = sys.stdout.isatty() and not (args.once or args.json)
    snapshot = None
    try:
        with terminal_keys(live) as keys:
            if live:
                sys.stdout.write("\033[?1049h\033[?25l")
            while True:
                error = None
                output = None
                log_id = None
                try:
                    snapshot = client.status(group=group)
                    if args.log:
                        log_id = next((t.id for t in snapshot.tasks if t.status == "Running"), None) if args.log == "auto" else int(args.log)
                        if log_id is not None:
                            output = client.log(log_id)
                except PueueError as exc:
                    error = str(exc)
                if args.json:
                    if error:
                        print(json.dumps({"error": error}, ensure_ascii=False))
                        return 1
                    print(json.dumps(asdict(snapshot), ensure_ascii=False, indent=2))
                    return 0
                size = shutil.get_terminal_size((100, 30))
                if live:
                    sys.stdout.write("\033[H\033[2J")
                if snapshot:
                    text = render(snapshot, width=size.columns, height=size.lines if live else max(30, 2*len(snapshot.tasks)+22),
                                  log_text=output, log_id=log_id, error=error)
                else:
                    text = f"pmon · {error}\n다시 연결 중 · q / Ctrl+C 종료"
                print(text, flush=True)
                if args.once:
                    return 1 if error else 0
                if keys:
                    ready, _, _ = select.select([sys.stdin], [], [], args.interval)
                    if ready and sys.stdin.read(1).lower() == "q":
                        return 0
                else:
                    time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        if live:
            sys.stdout.write("\033[?25h\033[?1049l")
            sys.stdout.flush()
