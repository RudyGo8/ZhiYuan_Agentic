'''
@create_time: 2025/11/15
@Author: GeChao
@File: test_tools.py
'''
import requests

url = "https://restapi.amap.com/v3/weather/weatherInfo"
params = {
    "key": "d7d989624ac74da0d1d895367037a536",
    "city": "上海",       # 换成你要查的城市 adcode
    "extensions": "base",   # base=实况, all=预报
    "output": "JSON"
}

resp = requests.get(url, params=params, timeout=10)
print(resp.json())
