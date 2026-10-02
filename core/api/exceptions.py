class APIException(Exception):
    """
    Encapsulates HTTP errors thrown by the microcosm API.
    """

    def __init__(self, error_message, status_code=None, detail=None):
        self.message = error_message
        self.status_code = status_code
        self.detail = detail
        super(APIException, self).__init__(error_message)

    def __str__(self):
        if self.status_code is None:
            return str(self.message)
        return 'HTTP status: %d: %s' % (self.status_code, self.message)
