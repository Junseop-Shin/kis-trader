# KIS Trader

## 프로젝트 개요

이 프로젝트는 한국투자증권(KIS) Open API를 활용하여 자동화된 투자 알고리즘을 개발하고 실행하기 위한 기반 환경을 제공합니다. Docker를 사용하여 환경을 격리하고, SQLite 데이터베이스를 통해 매매 기록 및 알고리즘 성과를 관리합니다.

## 필수 요구사항

- [Docker Desktop](https://www.docker.com/products/docker-desktop) (또는 Docker Engine)
- Python 3.9+ (개발 환경에서 스크립트 실행 시)

## 개발 환경 설정

### 1. 저장소 클론

```bash
git clone [저장소 URL]
cd kis_trader
```

### 2. 데이터 영속성을 위한 `data` 디렉토리 생성

SQLite 데이터베이스 파일(`trading_data.db`)이 호스트 시스템에 영구적으로 저장되도록 `data` 디렉토리를 생성합니다. 이 디렉토리는 Docker 컨테이너 내부의 `/app/data` 경로로 마운트됩니다.

```bash
mkdir -p data
```

### 3. `kis_devlp.yaml` 설정

`config/kis_devlp.yaml` 파일을 열어 다음 내용을 추가하거나 수정합니다. `database_path`는 컨테이너 내부 경로이며, `AppKey`와 `AppSecret`은 한국투자증권에서 발급받은 실제 키로 대체해야 합니다.

```yaml
# 데이터베이스 경로 설정
database_path: /app/data/trading_data.db

# KIS API 설정 (실제 키로 대체)
AppKey: "YOUR_APP_KEY"
AppSecret: "YOUR_APP_SECRET"
# ... 기타 KIS API 관련 설정
```

### 4. Docker 이미지 빌드

프로젝트 루트 디렉토리에서 다음 명령어를 실행하여 Docker 이미지를 빌드합니다.

```bash
docker build -t kis-trader .
```

### 5. 데이터베이스 초기화

**이 단계는 데이터베이스를 처음 설정할 때 또는 데이터베이스를 초기화하고 싶을 때만 실행합니다.**

`db_manager.py` 스크립트를 실행하여 SQLite 데이터베이스 파일(`trading_data.db`)을 생성하고 필요한 테이블들을 만듭니다. 이 파일은 위에서 생성한 호스트의 `data` 디렉토리에 저장됩니다.

```bash
docker run --rm -it \
  -v "$(pwd)/data:/app/data" \
  kis-trader \
  python db_manager.py
```

- `--rm`: 명령 실행 후 컨테이너를 자동으로 삭제합니다.
- `-it`: 인터랙티브 모드로 실행하여 스크립트의 출력을 볼 수 있습니다.
- `-v "$(pwd)/data:/app/data"`: 현재 작업 디렉토리의 `data` 폴더를 컨테이너 내부의 `/app/data` 폴더로 마운트합니다. 이렇게 함으로써 `trading_data.db` 파일이 호스트에 영구적으로 저장됩니다.
- `kis-trader`: 사용할 Docker 이미지 이름입니다.
- `python db_manager.py`: 컨테이너 내부에서 실행할 명령어입니다.

### 6. 애플리케이션 컨테이너 실행

데이터베이스 초기화가 완료되면, 이제 `trader.py` 스크립트와 cron 작업을 실행할 메인 애플리케이션 컨테이너를 시작합니다. 이 컨테이너도 데이터 영속성을 위해 `data` 볼륨을 마운트해야 합니다.

```bash
docker run -d --name kis-trader-container \
  -v "$(pwd)/data:/app/data" \
  kis-trader
```

- `-d`: 컨테이너를 백그라운드에서 실행합니다.
- `--name kis-trader-container`: 컨테이너에 이름을 부여하여 쉽게 관리할 수 있도록 합니다.

### 7. 컨테이너 로그 확인

컨테이너가 정상적으로 작동하는지 확인하려면 로그를 확인합니다. `trader.py` 스크립트의 출력은 컨테이너 내부의 `/tmp/cron.log` 파일에 기록됩니다.

```bash
docker exec kis-trader-container cat /tmp/cron.log
```

## 배포 고려사항

배포 환경에서는 `kis_devlp.yaml`의 민감한 정보(AppKey, AppSecret)를 환경 변수 등으로 관리하는 것이 좋습니다. Docker Secret이나 Kubernetes Secret 등을 활용할 수 있습니다. 데이터베이스 볼륨 관리도 배포 환경에 맞는 영구 스토리지 솔루션을 사용해야 합니다.

## 사용법

- **컨테이너 중지:** `docker stop kis-trader-container`
- **컨테이너 삭제:** `docker rm kis-trader-container`
- **이미지 삭제:** `docker rmi kis-trader`

## 문제 해결

- **`docker-credential-desktop` 오류:** Docker Desktop을 재시작하거나, `~/.docker/config.json` 파일에서 `"credsStore": "desktop"` 라인을 삭제해 보세요.
- **`python: not found` 또는 `python3: not found` 오류:** `crontab.txt`에서 `python` 또는 `python3` 대신 `/usr/local/bin/python3`와 같이 전체 경로를 사용했는지 확인하세요.
- **로그 파일이 생성되지 않음:** `kis_devlp.yaml`의 `database_path`가 올바른지, `data` 디렉토리가 호스트에 생성되었는지, `docker run` 명령에 `-v` 옵션이 올바르게 포함되었는지 확인하세요.
