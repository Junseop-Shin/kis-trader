import datetime
import sys
import os

# src 디렉토리를 sys.path에 추가하여 KISApi 모듈을 찾을 수 있도록 합니다.
# Docker 컨테이너의 /app/src 경로를 기준으로 설정합니다.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from kis_api import KISApi

def main():
    """
    메인 실행 함수.
    cron에 의해 주기적으로 실행됩니다.
    """
    print(f"[{datetime.datetime.now()}] Trader script is running...")
    
    try:
        # KISApi 인스턴스 생성 및 토큰 발급 시도
        # Docker 컨테이너 내의 절대 경로를 사용합니다.
        api = KISApi(config_path='/app/config/kis_config.yaml')
        token = api.get_access_token()
        if token:
            print("Token verification successful.")
        else:
            print("Token verification failed.")
            
    except FileNotFoundError:
        print("ERROR: Config file not found. Make sure /app/config/kis_config.yaml exists.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()