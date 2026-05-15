from abc import ABC, abstractmethod


class Piece(ABC):
    def __init__(self, color: str):
        self.color = color

    @abstractmethod
    def can_move(self, positions: dict, from_pos: int, to_pos: int) -> bool:
        pass

    @abstractmethod
    def can_capture(self, positions: dict, from_pos: int, to_pos: int, 
                    pending_captures: list[int] = None) -> bool:
        """pending_captures - для батыра, чтобы знать, кого уже съели в этом ходу"""
        pass

    @abstractmethod
    def get_type(self) -> str:
        pass

    def get_color(self) -> str:
        return self.color