class TranslationRetryManager:

    def __init__(self, max_attempts=3):
        self.max_attempts = max_attempts

    def should_retry(self, attempt, validation):
        """
        Determines whether another AI attempt
        should be performed.
        """

        if validation["valid"]:
            return False

        return attempt < self.max_attempts