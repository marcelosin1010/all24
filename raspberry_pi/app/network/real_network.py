""" This is a wrapper for network tables. """

# pylint: disable=R0902,R0903,W0212

# github workflow crashes in ntcore, bleah
import ntcore
from typing_extensions import override
from wpimath.geometry import Rotation3d

from app.config.identity import Identity
from app.network.network_protocol import (
    Blip24,
    Blip25,
    Blip25Receiver,
    Blip25Sender,
    BlipSender,
    DoubleSender,
    Network,
    NoteSender,
)


class RealDoubleSender(DoubleSender):
    def __init__(self, pub: ntcore.DoublePublisher) -> None:
        self.pub = pub

    @override
    def send(self, val: float, delay_us: int) -> None:
        self.pub.set(val, int(ntcore._now() - delay_us))


class RealBlipSender(BlipSender):
    def __init__(self, pub: ntcore.StructArrayPublisher) -> None:
        self.pub = pub

    @override
    def send(self, val: list[Blip24], delay_us: int) -> None:
        self.pub.set(val, int(ntcore._now() - delay_us))


class RealNoteSender(NoteSender):
    def __init__(self, pub: ntcore.StructArrayPublisher) -> None:
        self.pub = pub

    @override
    def send(self, val: list[Rotation3d], delay_us: int) -> None:
        self.pub.set(val, int(ntcore._now() - delay_us))


class RealBlip25Sender(Blip25Sender):
    def __init__(self, pub: ntcore.StructArrayPublisher) -> None:
        self.pub = pub

    @override
    def send(self, val: list[Blip25], delay_us: int) -> None:
        timestamp = int(ntcore._now() - delay_us)
        self.pub.set(val, timestamp)


class RealBlip25Receiver(Blip25Receiver):
    def __init__(self, sub: ntcore.StructArraySubscriber) -> None:
        self.sub = sub

    @override
    def get(self) -> list[tuple[int, list[Blip25]]]:
        recv = self.sub.readQueue()
        result: list[tuple[int, list[Blip25]]] = []
        for item in recv:
            server_time_us = item.serverTime
            value_list = item.value
            result.append((server_time_us, value_list))
        return result


class RealNetwork(Network):
    def __init__(self, identity: Identity) -> None:
        # TODO: use identity.name instead
        # TODO: make Network work for gyro, not just vision
        self._serial: str = identity.value
        self._inst: ntcore.NetworkTableInstance = (
            ntcore.NetworkTableInstance.getDefault()
        )
        self._inst.startClient4("tag_finder24")

        ntcore._now()

        # roboRio address. windows machines can impersonate this for simulation.
        # also localhost for testing
        if identity == Identity.UNKNOWN:
            # vasili says this doesn't work, but i need it for testing.
            self._inst.setServer("localhost")
        else:
            # this works
            self._inst.setServer("10.1.0.2")

    @override
    def get_double_sender(self, name: str) -> RealDoubleSender:
        return RealDoubleSender(self._inst.getDoubleTopic(name).publish())

    @override
    def get_blip_sender(self, name: str) -> RealBlipSender:
        return RealBlipSender(self._inst.getStructArrayTopic(name, Blip24).publish())

    @override
    def get_note_sender(self, name: str) -> RealNoteSender:
        return RealNoteSender(
            self._inst.getStructArrayTopic(name, Rotation3d).publish()
        )

    @override
    def get_blip25_sender(self, name: str) -> RealBlip25Sender:
        return RealBlip25Sender(self._inst.getStructArrayTopic(name, Blip25).publish())

    @override
    def get_blip25_receiver(self, name: str) -> Blip25Receiver:
        return RealBlip25Receiver(
            self._inst.getStructArrayTopic(name, Blip25).subscribe([])
        )

    @override
    def flush(self) -> None:
        self._inst.flush()