import time


def retry(attempts=3, base_delay=0.5, factor=2.0, retry_on=(Exception,), sleep=time.sleep):
    raise NotImplementedError
