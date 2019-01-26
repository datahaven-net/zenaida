from enum import Enum


class ChoiceEnum(Enum):

    @classmethod
    def choices_as_tuple(cls):
        return tuple((choice.name, choice.value) for choice in cls)

    @classmethod
    def choices_as_list(cls):
        return [choice.value for choice in cls]


class EPPStatusTypes(ChoiceEnum):
    EPP_STATUS_ACTIVE = 'ACTIVE'
    EPP_STATUS_INACTIVE = 'INACTIVE'
    EPP_STATUS_DEACTIVATED = 'DEACTIVATED'
    EPP_STATUS_CLIENT_HOLD = 'CLIENT HOLD'
    EPP_STATUS_SERVER_HOLD = 'SERVER HOLD'
    EPP_STATUS_TO_BE_DELETED = 'TO BE DELETED'
    EPP_STATUS_TO_BE_RESTORED = 'TO BE RESTORED'
    EPP_STATUS_UNKNOWN = 'UNKNOWN(ERROR)'
