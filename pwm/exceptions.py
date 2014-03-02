class DuplicateDomainException(Exception):
    """ Domain already exists. """


class NotReadyException(Exception):
    """ A database operation was attempted before pwm was connected to any. """
