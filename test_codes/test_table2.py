import base64
import urllib
import requests

API_KEY = "Id7EZH2q6IOSlivHbwHHbWwz"
SECRET_KEY = "leeZiDapOBp6nGZssuuzABgSZubNgSLu"


def main():
    url = "https://aip.baidubce.com/rest/2.0/ocr/v1/table?access_token=" + get_access_token()

    # image 可以通过 get_file_content_as_base64("C:\fakepath\银行3.png",True) 方法获取
    payload = 'image=%2Tez1ZrwAQOcFywuMPXfsJvx0nMRQ2nM5nUULqqzuz6K5%2BhNWJGSIqVTyGw6kDJ%2FmByMtG3LkD5gHM4eEK2HEqQSaQTnHrqgvurpN%2FJFdXH2neGoaF5J70tDSr8u6nOmaXbo0VvJE%2BJP2QvN9r1SD3vu6X5fE1nes%2FqRm8%2FcFjXE%2FTJeVIkQEY%2FUQDFRClkglxETuh2PSc9tNuw'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))

    response.encoding = "utf-8"
    print(response.text)


def get_file_content_as_base64(path, urlencoded=False):
    """
    获取文件base64编码
    :param path: 文件路径
    :param urlencoded: 是否对结果进行urlencoded
    :return: base64编码信息
    """
    with open(path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf8")
        if urlencoded:
            content = urllib.parse.quote_plus(content)
    return content


def get_access_token():
    """
    使用 AK，SK 生成鉴权签名（Access Token）
    :return: access_token，或是None(如果错误)
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {"grant_type": "client_credentials", "client_id": API_KEY, "client_secret": SECRET_KEY}
    return str(requests.post(url, params=params).json().get("access_token"))


if __name__ == '__main__':
    main()
