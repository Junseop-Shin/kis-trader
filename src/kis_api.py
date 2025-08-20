import yaml
import requests
import datetime

class KISApi:
    """
    한국투자증권 REST API와의 통신을 담당하는 클래스
    """
    def __init__(self, config_path='../config/kis_config.yaml'):
        """
        API 인스턴스를 초기화합니다.
        설정 파일에서 API 키와 기본 URL을 로드합니다.
        """
        self._load_config(config_path)
        self.access_token = None
        self.token_expires_at = None

    def _load_config(self, config_path):
        """설정 파일을 로드합니다."""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 실전 투자 계좌 정보를 우선으로 사용
        self.appkey = config.get('appkey')
        self.appsecret = config.get('appsecret')
        # 실전 투자 정보가 없으면 모의 투자 정보 사용
        if not self.appkey or not self.appsecret:
            self.appkey = config.get('virtual_appkey')
            self.appsecret = config.get('virtual_appsecret')
            
        self.base_url = "https://openapivts.koreainvestment.com:29443" # 모의투자 기본 URL
        # 실전 투자 키가 있을 경우 실전 투자 URL 사용 (URL 확인 필요)
        # if config.get('appkey'):
        #     self.base_url = "실전투자 URL" 

    def _issue_token(self):
        """인증 토큰을 발급받습니다."""
        url = f"{self.base_url}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        data = {
            "grant_type": "client_credentials",
            "appkey": self.appkey,
            "appsecret": self.appsecret
        }
        res = requests.post(url, headers=headers, json=data)
        if res.status_code == 200:
            token_data = res.json()
            self.access_token = token_data['access_token']
            # 토큰 만료 시간 관리 (예: 12시간)
            self.token_expires_at = datetime.datetime.now() + datetime.timedelta(seconds=token_data['expires_in'])
            print("Access Token issued successfully.")
        else:
            print(f"Error issuing token: {res.text}")
            self.access_token = None
            self.token_expires_at = None

    def get_access_token(self):
        """
        유효한 액세스 토큰을 반환합니다.
        토큰이 없거나 만료되었다면 새로 발급받습니다.
        """
        if self.access_token is None or self.token_expires_at < datetime.datetime.now():
            self._issue_token()
        return self.access_token

# 사용 예시
if __name__ == '__main__':
    # 설정 파일이 존재한다고 가정하고 테스트
    # 실제 사용 시에는 trader.py에서 이 클래스를 임포트하여 사용합니다.
    try:
        api = KISApi(config_path='../config/kis_config.yaml')
        token = api.get_access_token()
        if token:
            print(f"Access Token: {token}")
    except FileNotFoundError:
        print("Please create 'config/kis_config.yaml' from the template and fill in your API keys.")
    except Exception as e:
        print(f"An error occurred: {e}")
