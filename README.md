# Investor Flows Report

한국투자증권 Open API의 `국내기관_외국인 매매종목가집계` 데이터를 사용해 외국인과 기관이 동시에 순매수한 종목을 시장별로 선별하고, TOP 10 리포트 이미지를 생성한 뒤 Telegram과 MQWAY API로 전송하는 프로젝트입니다.

## 주요 기능

- KOSPI, KOSDAQ을 분리해 각각 TOP 10 이미지 생성
- 외국인 순매수량과 기관 순매수량이 모두 `0`을 초과하는 종목만 필터링
- 외국인+기관 합산 순매수량 기준 내림차순 TOP 10 선정
- 종목별 현재가, 30일 등락률, 외국인 순매수량, 기관 순매수량, 합산 순매수량, 합산 순매수 금액 표시
- 시장별 30일 지수 등락률을 표 상단 우측에 별도 표시
- 생성된 이미지 2장을 Telegram 미디어 그룹으로 전송
- MQWAY 게시글 API에 동일 이미지와 썸네일을 함께 업로드

## 산출물

실행 시 `img/` 폴더에 아래 형식의 이미지가 생성됩니다.

```text
img/investor_flows_kospi_top_report_YYYYMMDD.png
img/investor_flows_kosdaq_top_report_YYYYMMDD.png
```

MQWAY 업로드 썸네일은 아래 파일을 사용합니다.

```text
thumbnail/thumbnail.png
```

## 설치

Python 3.12 환경에서 검증했습니다.

```powershell
pip install -r requirements.txt
```

이미지 생성에는 `wkhtmltoimage`가 필요합니다. Windows 기준으로 `wkhtmltopdf`를 설치한 뒤 `.env`의 `WKHTMLTOIMAGE_PATH`에 실행 파일 경로를 설정합니다.

## 환경 변수

`.env.sample`을 복사해 `.env`를 만들고 값을 채웁니다.

```powershell
Copy-Item .env.sample .env
```

### 한국투자증권 Open API

```env
KIS_APP_KEY=your_app_key_here
KIS_APP_SECRET=your_app_secret_here
KIS_URL_BASE=https://openapi.koreainvestment.com:9443
```

### 이미지 렌더링

```env
WKHTMLTOIMAGE_PATH=C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltoimage.exe
```

### Telegram 전송

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_production_chat_id_here
TELEGRAM_CHAT_TEST_ID=your_test_chat_id_here
```

### MQWAY 게시글 API

```env
BASE_URL=http://example.com
```

## 실행

```powershell
python main.py
```

실행하면 한국 휴장일 여부를 먼저 확인합니다. 휴장일이 아니면 한국투자증권 API에서 시장지수와 외국인/기관 매매 데이터를 조회하고, 이미지 생성 후 Telegram 전송과 MQWAY API 호출까지 진행합니다.

운영 환경에서 실행하기 전에 `.env`의 Telegram 채팅 ID와 `BASE_URL`이 올바른 대상인지 확인해야 합니다.

## 테스트

```powershell
python -m pytest -v
python -m compileall main.py investor_flows utils tests
```

현재 테스트는 데이터 변환 로직, Telegram 유틸, MQWAY API 유틸의 주요 동작을 검증합니다.

## 프로젝트 구조

```text
.
├── main.py
├── investor_flows/
│   ├── __init__.py
│   └── transform.py
├── utils/
│   ├── __init__.py
│   ├── api_util.py
│   ├── logger_util.py
│   └── telegram_util.py
├── tests/
│   ├── test_delivery_utils.py
│   └── test_transform.py
├── thumbnail/
│   └── thumbnail.png
├── requirements.txt
├── token.json.sample
└── .env.sample
```

## 운영 참고

- `token.json`은 한국투자증권 접근 토큰 캐시 파일이며 저장소에 커밋하지 않습니다.
- `.env`, 생성 이미지, 로그 파일은 저장소에 커밋하지 않습니다.
- `BASE_URL`이 `localhost`라면 MQWAY 서버가 먼저 실행되어 있어야 합니다.
- MQWAY API 호출 실패 시 `TELEGRAM_CHAT_TEST_ID`로 오류 알림 전송을 시도합니다.
- `wkhtmltoimage` 경로가 잘못되면 이미지 생성 단계에서 실패합니다.
