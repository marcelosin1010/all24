# pylint: disable=R0902,R0903,W0212

from typing_extensions import override
from wpimath.geometry import Rotation3d

from app.network.network_protocol import (
    Blip24,
    Blip25,
    Blip25Receiver,
    BlipSender,
    DoubleSender,
    Network,
    NoteSender,
)


class FakeDoubleSender(DoubleSender):
    def __init__(self, doubles: list[float]) -> None:
        self.doubles = doubles

    @override
    def send(self, val: float, delay_us: int) -> None:
        self.doubles.append(val)


class FakeBlipSender(BlipSender):
    def __init__(self, blips: list[Blip24]) -> None:
        self.blips = blips

    @override
    def send(self, val: list[Blip24], delay_us: int) -> None:
        self.blips.extend(val)


class FakeNoteSender(NoteSender):
    def __init__(self, notes: list[Rotation3d]) -> None:
        self.notes = notes

    @override
    def send(self, val: list[Rotation3d], delay_us: int) -> None:
        self.notes.extend(val)


class FakeBlip25Sender(BlipSender):
    def __init__(self, blips: list[Blip25]) -> None:
        self.blips = blips

    @override
    def send(self, val: list[Blip25], delay_us: int) -> None:
        self.blips.extend(val)


class FakeBlip25Receiver(Blip25Receiver):
    def __init__(self) -> None:
        self.blips: list[tuple[int, list[Blip25]]] = []

    @override
    def get(self) -> list[tuple[int, list[Blip25]]]:
        return self.blips


class FakeNetwork(Network):
    def __init__(self) -> None:
        self.doubles: dict[str, list[float]] = {}
        self.blips: dict[str, list[Blip24]] = {}
        self.blip25s: dict[str, list[Blip25]] = {}
        self.notes: dict[str, list[Rotation3d]] = {}

    @override
    def get_double_sender(self, name: str) -> DoubleSender:
        if name not in self.doubles:
            self.doubles[name] = []
        return FakeDoubleSender(self.doubles[name])

    @override
    def get_blip_sender(self, name: str) -> BlipSender:
        if name not in self.blips:
            self.blips[name] = []
        return FakeBlipSender(self.blips[name])

    @override
    def get_note_sender(self, name: str) -> NoteSender:
        if name not in self.notes:
            self.notes[name] = []
        return FakeNoteSender(self.notes[name])

    @override
    def get_blip25_sender(self, name: str) -> BlipSender:
        if name not in self.blip25s:
            self.blip25s[name] = []
        return FakeBlip25Sender(self.blip25s[name])

    @override
    def get_blip25_receiver(self, name: str) -> Blip25Receiver:
        return FakeBlip25Receiver()

    @override
    def flush(self) -> None:
        pass