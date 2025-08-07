# 커스텀 예외 클래스
class ApiException(RuntimeError):
    def __init__(self, error_code: str, message: str = None):
        self.error_code = error_code
        self.message = message
        super().__init__(self.message)