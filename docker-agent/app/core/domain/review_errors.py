class ReviewUnavailableError(RuntimeError):
    pass


class ReviewInteractionNotFoundError(RuntimeError):
    pass


class ReviewInteractionAlreadyEvaluatedError(RuntimeError):
    def __init__(self, *, interaction_id: int, review_status: str) -> None:
        self.interaction_id = interaction_id
        self.review_status = review_status
        super().__init__(f"Interacao {interaction_id} ja foi avaliada ({review_status}).")


class ReviewValidationError(ValueError):
    pass
