# KIA Vehicle KR for Home Assistant

![KIA Movement that inspires 로고](custom_components/kia_vehicle_kr/brand/logo.png)

KIA Developers의 국내 커넥티드카 API를 Home Assistant에서 사용할 수 있도록 연결하는 커스텀 통합입니다.

## 경고

- 본 커스텀 컴포넌트는 KIA의 공식 프로젝트가 아니며 개인 사용에 한정합니다.
- 이 통합이 사용하는 KIA Developers API는 한국 서버에서만 유효합니다. 다른 국가의 KIA 계정 및 서버와는 호환되지 않습니다.

## 주요 기능

- Home Assistant 와 KIA API을 이용하여 주행 가능/누적 주행거리 조회 할수 있습니다.
- 해당 API로는 차량 위치 조회는 불가능합니다.

## 사용 전 준비

> [!CAUTION]
> 데이터 조회시 KIA Connect 서비스 계약이 필요합니다.

### 1. KIA Developers 프로젝트 생성

Client ID와 Client Secret의 발급 및 관리는 [KIA 개발자 센터](https://developers.kia.com/)에서 할 수 있습니다.

KIA 개발자 센터에서 프로젝트를 생성한 뒤, 이 통합에 필요한 계정 API와 차량 API를 활성화하십시오.

API 이용 가능 여부와 권한은 프로젝트 유형 및 KIA의 승인 상태에 따라 달라질 수 있습니다.

### 2. 콜백 URL 등록

KIA Developers 프로젝트에 다음 URL을 등록해야 합니다.

#### 계정 API Redirect URL

통합 설정 화면에 표시되는 설치별 주소를 등록하십시오. 일반적인 형식은 다음과 같습니다.

```text
<HOME_ASSISTANT_URL>/api/KIA_vehicle_kr/oauth/callback
```

#### 데이터 API Redirect URL

차량 목록 API가 별도 개인정보 제공 동의를 요구하는 경우에만 필요합니다.

```text
<HOME_ASSISTANT_URL>/api/KIA_vehicle_kr/consent/callback
```

> [!IMPORTANT]
>
> 두 Redirect URL 모두 브라우저와 KIA 인증 서버에서 접근할 수 있는 HTTPS 주소여야 합니다.
> 내부 IP, `.local` 주소 또는 외부에서 접근할 수 없는 주소는 정상적으로 동작하지 않을 수 있습니다.

## 설치

### HACS 사용자 지정 저장소

1. HACS에서 **사용자 지정 저장소**를 엽니다.
2. 이 저장소 주소를 추가하고 카테고리로 **Integration**을 선택합니다.
3. **KIA Vehicle KR**을 설치합니다.
4. Home Assistant를 다시 시작합니다.
5. **설정 → 기기 및 서비스 → 통합 구성요소 추가**에서 **KIA Vehicle KR**을 선택합니다.

### 수동 설치

1. 이 저장소의 `custom_components/kia_vehicle_kr` 폴더를 Home Assistant 설정 디렉터리의 `custom_components` 아래에 복사합니다.
2. 최종 경로가 다음과 같은지 확인합니다.

   ```text
   <HOME_ASSISTANT_CONFIG>/custom_components/kia_vehicle_kr
   ```

3. Home Assistant를 다시 시작합니다.
4. **설정 → 기기 및 서비스 → 통합 구성요소 추가**에서 **KIA Vehicle KR**을 선택합니다.

## 설정 방법

1. 통합 추가 화면에서 KIA 개발자 센터가 발급한 Client ID와 Client Secret을 입력합니다.
2. 화면에 표시된 계정 API 콜백 URL이 KIA Developers 프로젝트에 등록된 값과 일치하는지 확인합니다. Data API Redirect URL은 KIA가 별도 동의를 요구하는 경우에만 등록합니다.
3. KIA 로그인 및 차량 이용 동의를 완료합니다.
4. 조회된 차량 목록에서 Home Assistant에 추가할 차량을 한 대 이상 선택합니다.

인증이 끝나면 선택한 차량마다 Home Assistant 장치와 엔티티가 만들어집니다. 이후 통합 항목의 **구성**을 누르면 차량 선택과 상태 조회 주기를 변경할 수 있습니다.

## 제공 엔티티

차량마다 다음 엔티티가 생성됩니다.

- **주행 가능 거리 센서**: 차량이 보고한 주행 가능 거리를 km 단위로 표시합니다.
- **누적 주행거리 센서**: KIA의 최신 주행거리 기록을 km 단위로 표시합니다. 별도 API 권한이 없거나 조회에 실패하면 이 센서만 사용할 수 없음으로 표시됩니다.
- **새로고침 버튼**: 선택한 차량의 정보를 즉시 다시 조회합니다.

기본 자동 조회 주기는 15분이며, 통합 구성 화면에서 변경할 수 있습니다. KIA API 호출 한도를 고려해 지나치게 짧은 주기는 사용하지 않는 것이 좋습니다.

## 월별 주행거리 보기

누적 주행거리 센서는 Home Assistant의 장기 통계에 등록됩니다. 매월 주행한 거리를 **보기만** 하려면 대시보드에 **통계 그래프** 카드를 추가하고, 차량의 누적 주행거리 센서를 선택한 뒤 통계 유형을 **변화량(change)**, 기간을 **월(month)**로 설정하십시오. 월별 주행거리는 해당 기간에 증가한 누적 주행거리로 표시됩니다. 아래는 카드 코드 편집기를 사용할 때의 예시이며, `sensor.kia_odometer`를 실제 차량의 엔티티 ID로 바꿔야 합니다.

```yaml
type: statistics-graph
title: 월별 주행거리
entities:
  - sensor.KIA_odometer
stat_types:
  - change
period: month
days_to_show: 365
chart_type: bar
```

## 이달의 주행거리

- 이번 달 주행거리를 **별도 센서**로 보고 싶다면 **설정 → 기기 및 서비스 → 도우미 → 도우미 만들기 → Utility Meter**를 추가하십시오.
- 입력 센서로 누적 주행거리 센서를 선택하고, 재설정 주기를 **월간**, 오프셋을 **0일**로 설정합니다.
- `Delta values`와 `Net consumption`은 끄고, 차량의 누적 주행거리가 주기적으로 0으로 재설정되지 않는다면 `Periodically resetting`도 끕니다.
- 이 도우미는 Home Assistant 설정 시간대의 매월 1일 0시에 0으로 돌아가며, 직전 달 값은 `last_period` 속성에 남습니다.
- Home Assistant를 재시작해도 값이 복원됩니다.

두 방법 모두 기록을 시작하기 전의 주행거리를 소급해서 만들 수는 없으므로 첫 달은 부분 기록입니다.

**참고**

- 데이터의 갱신 주기 때문에 월 경계 시각의 주행거리는 마지막·첫 API 조회 시각 기준으로 근사됩니다.
- 장기 통계를 사용하려면 Home Assistant의 Recorder에서 누적 주행거리 센서를 제외하지 않아야 합니다.

## 여러 차량 사용

하나의 KIA 계정에 여러 차량이 등록되어 있으면 최초 인증 직후 차량 선택 화면이 표시됩니다. (다만 제가 차량이 1대라 확인은 못했습니다.)
개념상 여러 대를 동시에 선택할 수 있으며, 선택한 차량은 각각 별도의 Home Assistant 장치로 등록됩니다.

만약 데이터 추가 이후 차량을 추가하거나 제외하려면 **설정 → 기기 및 서비스 → KIA Vehicle KR → 구성**으로 이동하십시오.

## 개인정보 및 보안

- Client ID, Client Secret 및 OAuth 토큰은 Home Assistant의 Application Credentials와 구성 항목 저장소를 통해 관리됩니다.
- 진단 정보에서는 액세스 토큰, 갱신 토큰 및 차량 식별자를 제외합니다.
- 선택 해제되거나 더 이상 조회할 수 없는 차량 데이터는 이 통합이 별도로 보관하지 않습니다. 다만 기존 상태는 Home Assistant의 기록 보존 설정에 따라 데이터베이스에 남아 있을 수 있습니다.
- Home Assistant 백업을 외부에 공유할 때에는 인증 정보가 포함될 수 있으므로 주의하십시오.

## 문제 해결

### 로그인 후 Home Assistant로 돌아오지 않는 경우

- KIA 개발자 센터에 등록한 계정 API Redirect URL과 설정 화면에 표시된 URL이 정확히 같은지 확인하십시오.
- Home Assistant의 외부 URL과 HTTPS 설정을 확인하십시오.
- OAuth 콜백 주소에서 404가 나오면 실제 Home Assistant의 통합 버전이 0.2.1 이상인지 확인하고, 전체 파일을 다시 설치한 뒤 Home Assistant를 재시작하십시오.

### 개인정보 동의 후 차량 목록이 표시되지 않는 경우

- Data API Redirect URL이 외부에서 접근 가능한지 확인하십시오.
- KIA Developers 프로젝트에 차량 API가 활성화되어 있는지 확인하십시오.
- 해당 프로젝트에서 이용할 차량이 등록 또는 승인되어 있는지 확인하십시오.

### 차량이 보이지 않는 경우

- 동일한 KIA 계정으로 차량이 정상 등록되어 있는지 확인하십시오.
- KIA 개발자 센터의 프로젝트 권한과 차량 등록 상태를 확인하십시오.
- 통합을 다시 인증한 뒤 차량 선택 화면을 확인하십시오.

## 사용 API

현재 다음 KIA Developers API를 사용합니다.

- OAuth 인증 및 토큰 발급
- 사용자 프로필 조회
- 차량 목록 조회
- 차량별 주행 가능 거리 조회
- 차량별 누적 주행거리 조회

API 주소와 세부 요청 형식은 `custom_components/kia_vehicle_kr`의 구현을 참고하십시오.

## 면책 고지

- 본 커스텀 컴포넌트는 KIA의 공식 프로젝트가 아니며 개인 사용에 한정합니다. 사용함에 있어서 발생하는 이슈는 사용자 책임에 있습니다.
- Client ID 발급 및 관리는 [KIA 개발자 센터](https://developers.KIA.com/)에서 가능합니다.

- KIA 개발자 프로젝트에서 누적 주행거리 API 권한이 없으면 해당 센서는 사용할 수 없음으로 표시될 수 있습니다.
- KIA API 응답 형식이나 정책이 변경되면 일시적으로 작동하지 않을 수 있습니다.
- KIA가 문서화한 회원 탈퇴, 차량 삭제 및 개인정보 제공 동의 철회 통보용 Data API 콜백은 설치 시 사용하는 동의 콜백과 별개의 기능입니다.
- 불특정 다수를 대상으로 배포하거나 상용으로 운영하려면 KIA의 정책, 심사 및 콜백 요구사항을 별도로 확인해야 합니다.

## 기타

**KIA 및 관련 명칭과 상표는 각 권리자의 자산입니다.**

- 이 프로젝트는 기아자동차와 제휴하거나, 기아자동차의 보증을 받은 프로젝트가 아닙니다.
- 본 컴포넌트를 사용하면서 발생하는 문제와 손해에 대한 책임은 사용자에게 있습니다.
