class CiderException(Exception):  # Generic CIDER exception
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CiderRenderingException(CiderException):  # When widgets won't render
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CiderBadActionException(CiderException):  # Generic bad action
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CiderInvalidConfigurationException(
    CiderBadActionException
):  # When config is totally invalid
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class CiderInvalidConfigSettingException(CiderInvalidConfigurationException):
    # Slightly more expressive exception for when the configuration setting is somehow invalid
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
