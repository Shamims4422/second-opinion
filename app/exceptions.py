class CriticLoopError(Exception):
    """Base for domain errors rendered as {"error": {"code", "message"}} responses."""

    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ExperienceNotFoundError(CriticLoopError):
    status_code = 404
    code = "EXPERIENCE_NOT_FOUND"

    def __init__(self, experience_id: int) -> None:
        super().__init__(f"No experience exists with ID {experience_id}.")


class DuplicateOutcomeError(CriticLoopError):
    status_code = 409
    code = "DUPLICATE_OUTCOME"

    def __init__(self, experience_id: int) -> None:
        super().__init__(
            f"An outcome has already been recorded for experience {experience_id}."
        )
