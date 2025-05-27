class Response:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def json(self):
        return {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP error")

class Session:
    def __init__(self):
        self.headers = {}
        self.proxies = {}

    def get(self, *args, **kwargs):
        return Response()

    def post(self, *args, **kwargs):
        return Response()

    def mount(self, *args, **kwargs):
        pass

class HTTPAdapter:
    def __init__(self, *args, **kwargs):
        pass

class exceptions:
    class ProxyError(Exception):
        pass
    class ConnectTimeout(Exception):
        pass
    class ReadTimeout(Exception):
        pass
    class ConnectionError(Exception):
        pass
