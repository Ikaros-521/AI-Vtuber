from sparkdesk_web.core import SparkWeb
from sparkdesk_api.core import SparkAPI

sparkWeb = SparkWeb(
    cookie="",
    fd="",
    GtToken=""
)

sparkAPI = SparkAPI(
    app_id="",
    api_secret="",
    api_key=""
)

 # single chat
print(sparkWeb.chat("repeat: hello world"))
print(sparkAPI.chat("repeat: hello world"))