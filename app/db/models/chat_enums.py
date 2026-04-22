from enum import Enum


class ChatAnswerStatus(str, Enum):
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    NO_ANSWER = "NO_ANSWER"
    ERROR = "ERROR"
