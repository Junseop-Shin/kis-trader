import yaml
import requests
import datetime

class KISApi:
    """
    한국투자증권 REST API와의 통신을 담당하는 클래스
    """
    def __init__(self, config_path='config/kis_config.yaml', is_real_trading=False):
        """
        API 인스턴스를 초기화합니다.
        설정 파일에서 API 키와 기본 URL을 로드합니다.
        Args:
            config_path (str): Path to the configuration YAML file.
            is_real_trading (bool): True for real trading, False for virtual trading.
        """
        self.is_real_trading = is_real_trading
        self._load_config(config_path)
        self.access_token = None
        self.token_expires_at = None

    def _load_config(self, config_path):
        """설정 파일을 로드합니다."""
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        

        if self.is_real_trading:
            real_config = config.get('real', {})
            self.account_no = real_config.get('account_no', '')
            self.appkey = real_config.get('appkey')
            self.appsecret = real_config.get('appsecret')
            self.base_url = f"{real_config.get('base_url')}:{real_config.get('port')}"
        else:
            virtual_config = config.get('virtual', {})
            self.account_no = virtual_config.get('account_no', '')
            self.appkey = virtual_config.get('appkey')
            self.appsecret = virtual_config.get('appsecret')
            self.base_url = f"{virtual_config.get('base_url')}:{virtual_config.get('port')}"

    def _issue_token(self):
        """
        인증 토큰을 발급받습니다.
        """
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
            self.token_expires_at = datetime.datetime.now() + datetime.timedelta(seconds=token_data.get('expires_in', 3600))
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

    def get_account_balance(self):
        """
        주식 잔고 현황을 조회합니다.
        [참고] 한국투자증권 API 문서: 국내주식 잔고조회
        실전: https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance (tr_id: TTTC8434R)
        모의: https://openapivts.koreainvestment.com:29443/uapi/domestic-stock/v1/trading/inquire-balance (tr_id: VTTC8434R)
        
        tr_id (Transaction ID): API 호출 유형을 식별하는 고유한 값입니다.
        각 API 요청마다 정해진 tr_id를 헤더에 포함하여 전송해야 합니다.
        """
        print("Fetching account balance...")
        
        token = self.get_access_token()
        if not token:
            print("Failed to get access token for balance inquiry.")
            return None
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
            "tr_id": "VTTC8434R" if not self.is_real_trading else "TTTC8434R" # Using virtual trading TR ID
        }
        params = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "01",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
        
        try:
            res = requests.get(url, headers=headers, params=params)
            if res.status_code == 200:
                return res.json()
            else:
                print(f"Error fetching account balance: {res.text}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Network error fetching account balance: {e}")
            return None

    def order_stock(self, side: str, symbol: str, quantity: int, price: float):
        """
        주식 매수/매도 주문을 실행합니다.
        """
        print(f"Placing order: {side} {quantity} of {symbol} at {price}")
        
        token = self.get_access_token()
        if not token:
            print("Failed to get access token for order.")
            return {"success": False, "message": "No access token"}
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "appkey": self.appkey,
            "appsecret": self.appsecret,
            "tr_id": "VTTC0802U" if not self.is_real_trading else "TTTC0802U" if side == 'buy' else "TTTC0801U" # 매수/매도 tr_id
        }
        data = {
            "CANO": self.account_no.split('-')[0],
            "ACNT_PRDT_CD": self.account_no.split('-')[1],
            "PDNO": symbol,
            "ORD_DVSN": "01", # 시장가
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price), # 지정가
            "CTRT_EXP_DT": "",
            "PDNO_FLG": "",
            "PRCS_DVSN": "",
            "IVRS_PRCS_DVSN": ""
        }
        url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
        
        try:
            res = requests.post(url, headers=headers, json=data)
            if res.status_code == 200:
                return {"success": True, "data": res.json()}
            else:
                print(f"Error placing order: {res.text}")
                return {"success": False, "message": res.text}
        except requests.exceptions.RequestException as e:
            print(f"Network error placing order: {e}")
            return {"success": False, "message": str(e)}

# 사용 예시
if __name__ == '__main__':
    try:
        api = KISApi()
        balance = api.get_account_balance()
        if balance and balance['rt_cd'] == '0':
            total_balance = balance['output2']['tot_evlu_amt']
            print(f"Total account balance: {total_balance}")

        # Test order_stock
        # order_result = api.order_stock(side='buy', symbol='005930', quantity=1, price=70000)
        # print(f"Order result: {order_result}")

    except FileNotFoundError:
        print("Please ensure 'config/kis_config.yaml' exists and is correctly configured.")
    except Exception as e:
        print(f"An error occurred: {e}")
