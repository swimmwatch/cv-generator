import enum


class VideoProcessingStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    REJECTED = "rejected"
    DONE = "done"


class VideoRejectReasonCode(enum.StrEnum):
    NO_CAPTIONS = "no_captions"
    AUTO_ONLY = "auto_only"
    WRONG_LANGUAGE = "wrong_language"
    LOW_COVERAGE = "low_coverage"
    LIVE = "live"
    DURATION_OUT_OF_RANGE = "duration_out_of_range"
    UNAVAILABLE = "unavailable"
    LOW_QUALITY = "low_quality"
    TOOL_ERROR = "tool_error"
