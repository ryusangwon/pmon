# pmon 사용 설명

**pueue의 작업 대기열을 실시간으로 보여주는 범용 모니터**입니다.
Python 패키지와 CLI를 제공하며 특정 프로젝트나 애플리케이션에 종속되지 않습니다.

## 설치와 실행

Python 3.11 이상에서 설치합니다.

```bash
python -m pip install pueue-pmon
pmon --config /path/to/pueue.yml
```

`pmon` 명령을 찾지 못하면 설치한 Python 환경을 활성화하거나 다음처럼 실행합니다.

```bash
python -m pmon --config /path/to/pueue.yml
```

OS별 wheel에는 공식 pueue·pueued 4.0.4 실행 파일이 포함됩니다.
별도 Homebrew/Cargo 설치는 필요 없지만, **조회할 pueue daemon은 실행 중이어야
합니다.** 패키지 설치나 모니터 실행만으로 daemon을 시작하거나 작업을 등록하지
않습니다. macOS ARM64는 실제 실행을 검증했으며 다른 플랫폼은 추가 실행 검증이
필요합니다.

## `.pueue` 폴더가 꼭 필요한가요?

필요하지 않습니다. `.pueue`는 설정·상태 등을 보관하는 폴더 이름의 한 예일
뿐입니다. pmon에 필요한 것은 **연결할 pueue daemon의 기존 설정 파일**입니다.
설정 파일은 이름이나 위치가 달라도 됩니다.

```bash
pmon --config /원하는/위치/pueue.yml
```

프로젝트마다 폴더를 만들거나 코드를 수정할 필요가 없습니다. 여러 프로젝트가
동일한 daemon을 사용하면 같은 설정으로 연결하고 그룹별로 볼 수 있습니다.

```bash
pmon --config /path/to/pueue.yml --group training
pmon --config /path/to/pueue.yml --group downloads
```

다른 daemon을 보고 싶으면 그 daemon의 설정 파일을 지정합니다. 상태·소켓·로그의
실제 저장 위치는 pmon이 아닌 연결 대상 pueue의 설정에 따릅니다.

## 자주 사용하는 옵션

| 명령 옵션 | 기능 |
|---|---|
| `--group NAME` | 특정 그룹만 표시 |
| `--log` | 실행 중인 첫 작업의 최근 로그 |
| `--log 2` | 작업 ID 2의 최근 로그 |
| `--interval 5` | 5초마다 갱신 (기본: 2초) |
| `--once` | 한 번만 출력하고 종료 |
| `--json` | 환경변수를 제외한 상태 JSON 출력 |
| `--profile NAME` | pueue 설정의 특정 profile 사용 |

화면에서 `r`은 즉시 갱신, `q` 또는 `Ctrl+C`는 모니터만 종료합니다.
실행·대기 중인 작업은 계속 유지됩니다.

## 설정 경로를 매번 입력하기 싫다면

실행할 폴더에 `pmon.toml`을 만듭니다.

```toml
[connection]
config = "/path/to/pueue.yml"
group = "training"  # 생략하면 전체 그룹
```

이후 해당 폴더에서 `pmon`만 실행합니다. 상대 경로는 TOML 파일 기준이며,
`--settings /path/to/pmon.toml`로 다른 설정을 선택할 수 있습니다.
명시적인 CLI 옵션이 설정 파일보다 우선합니다.

## 보여주는 정보

- 실행·대기·정지·완료·실패 상태
- 작업 이름과 명령, 그룹, 경과 시간, 작업 간 의존성
- 선택한 작업의 최근 출력

pmon은 pueue의 `status`와 `log`만 읽습니다. 프로그램 내부의 완료 비율을
추정하거나 애플리케이션 상태 파일을 읽지 않으며, 별도의 계측 코드를 요구하지
않습니다. task 환경변수는 표시하지 않습니다. 로그에는 작업이 출력한 내용이
그대로 포함될 수 있습니다.

포함된 upstream 도구는 `pmon-pueue`, `pmon-pueued`로 실행할 수 있습니다.
이 두 명령은 upstream 기능을 제공하는 별도 도구이며, 모니터 자체는 읽기 전용입니다.
도구를 직접 실행할 때는 `--config` 또는 `PUEUE_CONFIG_PATH`를 지정하세요.

## Python API

```python
from pmon import Client

client = Client("/path/to/pueue.yml")
for task in client.status(group="training").tasks:
    print(task.id, task.status, task.label)
```

[영문 README](README.md) · [PyPI](https://pypi.org/project/pueue-pmon/)
