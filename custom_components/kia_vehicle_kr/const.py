"""Constants for the Kia Developers integration."""

from datetime import timedelta

DOMAIN = "kia_vehicle_kr"

AUTHORIZE_URL = "https://prd.kr-ccapi.kia.com/api/v1/user/oauth2/authorize"
TOKEN_URL = "https://prd.kr-ccapi.kia.com/api/v1/user/oauth2/token"
PROFILE_URL = "https://prd.kr-ccapi.kia.com/api/v1/user/profile"
DATA_API_BASE_URL = "https://dev.kr-ccapi.kia.com/api/v1"
VEHICLES_URL = f"{DATA_API_BASE_URL}/car/profile/carlist"
CONSENT_URL = f"{DATA_API_BASE_URL}/car-service/terms/agreement"
CONSENT_CALLBACK_PATH = "/api/kia_vehicle_kr/consent/callback"
OAUTH_CALLBACK_PATH = "/api/kia_vehicle_kr/oauth/callback"

CONF_VEHICLE_IDS = "vehicle_ids"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_UPDATE_INTERVAL_MINUTES = 15
MIN_UPDATE_INTERVAL_MINUTES = 5
MAX_UPDATE_INTERVAL_MINUTES = 1440
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL_MINUTES)

