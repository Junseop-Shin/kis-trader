# Python 3.9 버전을 기반으로 이미지를 생성합니다.
FROM python:3.9-slim

# 작업 디렉토리를 /app 으로 설정합니다.
WORKDIR /app

# 필요한 시스템 패키지를 설치합니다. (cron 추가)
RUN apt-get update && apt-get install -y cron

# 프로젝트의 모든 파일을 /app 디렉토리로 복사합니다.
COPY . .

# requirements.txt 파일에 명시된 파이썬 패키지들을 설치합니다.
RUN pip install --no-cache-dir -r requirements.txt

# crontab.txt 파일을 시스템의 crontab에 추가하고 권한을 설정합니다.
RUN crontab crontab.txt

# 컨테이너가 시작될 때 cron 데몬을 실행합니다.
CMD ["cron", "-f"]
