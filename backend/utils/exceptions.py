class ResumeVerificationError(Exception):
    def __init__(self, message: str = "Resume verification failed", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class OCRProcessingError(Exception):
    def __init__(self, message: str = "Certificate verification failed", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class BlockchainError(Exception):
    def __init__(self, message: str = "Blockchain verification failed", status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
