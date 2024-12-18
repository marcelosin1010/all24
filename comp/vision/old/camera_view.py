# pylint: disable=C0103,C0114,C0115,C0116,E0401,R0902,R0915,W0201

import dataclasses
import pprint
import sys
import time
from enum import Enum
from typing import Any, cast

import cv2
import ntcore
import numpy as np
import robotpy_apriltag
from cscore import CameraServer
from numpy.typing import NDArray
from picamera2 import CompletedRequest, Picamera2  # type: ignore
from wpimath.geometry import Transform3d
from wpiutil import wpistruct

Mat = NDArray[np.uint8]


@wpistruct.make_wpistruct # type: ignore
@dataclasses.dataclass
class Blip24:
    id: int
    pose: Transform3d


class Camera(Enum):
    """Keep this synchronized with java team100.config.Camera."""

    A = "10000000caeaae82"  # "BETA FRONT"
    C = "10000000a7c673d9"  # "GAMMA INTAKE"

    SHOOTER = "10000000a7a892c0"  # "DELTA SHOOTER"
    RIGHTAMP = "10000000caeaae82"  # "DELTA AMP-PLACER"
    LEFTAMP = "100000004e0a1fb9"  # "DELTA AMP-PLACER"
    GAME_PIECE = "1000000013c9c96c"  # "DELTA INTAKE"

    G = "10000000a7a892c0"  # ""
    UNKNOWN = None

    @classmethod
    def _missing_(cls, value: object) -> "Camera":
        return Camera.UNKNOWN


class CameraData:
    def __init__(self, camera_num: int) -> None:
        self.camera = Picamera2(camera_num)
        model: str = cast(str, self.camera.camera_properties["Model"])  # type:ignore
        print("\nMODEL " + model)
        self.id = camera_num

        if model == "imx708_wide":
            print("V3 Wide Camera")
            # full frame is 4608x2592; this is 2x2
            fullwidth = 2304
            fullheight = 1296
            # medium detection resolution, compromise speed vs range
            self.width: int = 1152
            self.height: int = 648
        elif model == "imx219":
            print("V2 Camera")
            # full frame, 2x2, to set the detector mode to widest angle possible
            fullwidth = 1664  # slightly larger than the detector, to match stride
            fullheight = 1232
            # medium detection resolution, compromise speed vs range
            self.width: int = 832
            self.height: int = 616
        elif model == "imx296":
            print("GS Camera")
            # full frame, 2x2, to set the detector mode to widest angle possible
            fullwidth = 1408  # slightly larger than the detector, to match stride
            fullheight = 1088
            # medium detection resolution, compromise speed vs range
            self.width: int = 1408
            self.height: int = 1088
        else:
            print("UNKNOWN CAMERA: " + model)
            fullwidth: int = 100
            fullheight = 100
            self.width: int = 100
            self.height = 100

        camera_config: dict[str, Any] = (
            self.camera.create_still_configuration(  # type:ignore
                # 2 buffers => low latency (32-48 ms), low fps (15-20)
                # 5 buffers => mid latency (40-55 ms), high fps (22-28)
                # 3 buffers => high latency (50-70 ms), mid fps (20-23)
                # robot goes at 50 fps, so roughly a frame every other loop
                # fps doesn't matter much, so minimize latency
                buffer_count=2,
                main={
                    "format": "YUV420",
                    "size": (fullwidth, fullheight),
                },
                lores={"format": "YUV420", "size": (self.width, self.height)},
                controls={
                    # these manual controls are useful sometimes but turn them off for now
                    # because auto mode seems fine
                    # fast shutter means more gain
                    # "AnalogueGain": 8.0,
                    # try faster shutter to reduce blur.  with 3ms, 3 rad/s seems ok.
                    # 3/23/24, reduced to 2ms, even less blur.
                    "ExposureTime": 3000,
                    "AnalogueGain": 8,
                    # "AeEnable": True,
                    # limit auto: go as fast as possible but no slower than 30fps
                    # without a duration limit, we slow down in the dark, which is fine
                    # "FrameDurationLimits": (5000, 33333),  # 41 fps
                    # noise reduction takes time, don't need it.
                    "NoiseReductionMode": 0,  # libcamera.controls.draft.NoiseReductionModeEnum.Off,
                    # "ScalerCrop":(0,0,width/2,height/2),
                },
            )
        )
        print("SENSOR MODES AVAILABLE")
        pprint.pprint(self.camera.sensor_modes) # type: ignore
        print("\nREQUESTED CONFIG")
        print(camera_config)
        self.camera.align_configuration(camera_config) # type: ignore
        print("\nALIGNED CONFIG")
        print(camera_config)
        self.camera.configure(camera_config) # type: ignore
        print("\nCONTROLS")
        print(self.camera.camera_controls) # type: ignore
        if model == "imx708_wide":
            print("V3 WIDE CAMERA")
            fx = 498
            fy = 498
            cx = 584
            cy = 316
            k1 = 0.01
            k2 = -0.0365
        elif model == "imx219":
            print("V2 CAMERA (NOT WIDE ANGLE)")
            fx = 660
            fy = 660
            cx = 426
            cy = 303
            k1 = -0.003
            k2 = 0.04
        # TODO get these real distortion values
        elif model == "imx296":
            fx = 1680
            fy = 1680
            cx = 728
            cy = 544
            k1 = 0
            k2 = 0
        else:
            print("UNKNOWN CAMERA MODEL")
            sys.exit()
        tag_size = 0.1651
        p1 = 0
        p2 = 0
        self.mtx = np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]])
        self.dist = np.array([[k1, k2, p1, p2]])
        self.output_stream = CameraServer.putVideo(
            str(camera_num), self.width, self.height
        )
        self.estimator = robotpy_apriltag.AprilTagPoseEstimator(
            robotpy_apriltag.AprilTagPoseEstimator.Config(
                tag_size,
                fx,
                fy,
                cx,
                cy,
            )
        )
        self.camera.start()  # type: ignore
        self.frame_time = time.time()
        self.fps: float = 0

    def setFPSPublisher(self, FPSPublisher: ntcore.DoublePublisher) -> None:
        self.FPSPublisher = FPSPublisher

    def setLatencyPublisher(self, LatencyPublisher: ntcore.DoublePublisher) -> None:
        self.LatencyPublisher = LatencyPublisher


class Test:
    def __init__(self, serial: str, camList: list[CameraData]) -> None:
        # the cpu serial number
        self.serial = serial
        self.initialize_nt(camList)

    def initialize_nt(self, camList: list[CameraData]) -> None:
        """Start NetworkTables with Rio as server, set up publisher."""
        self.inst = ntcore.NetworkTableInstance.getDefault()
        self.inst.startClient4("tag_finder24")
        # roboRio address. windows machines can impersonate this for simulation.
        self.inst.setServer("10.1.0.2")

        topic_name = "vision/" + self.serial
        for camera in camList:
            camera.setFPSPublisher(
                self.inst.getDoubleTopic(
                    topic_name + "/" + str(camera.id) + "/fps"
                ).publish()
            )
            camera.setLatencyPublisher(
                self.inst.getDoubleTopic(
                    topic_name + "/" + str(camera.id) + "/latency"
                ).publish()
            )

        # work around https://github.com/robotpy/mostrobotpy/issues/60
        self.inst.getStructTopic("bugfix", Blip24).publish().set(
            Blip24(0, Transform3d())
        )
        # blip array topic
        self.vision_nt_struct = self.inst.getStructArrayTopic(
            topic_name + "/blips", Blip24
        ).publish()

        self.estimatedTagPose = self.inst.getStructArrayTopic(
            topic_name + "/estimatedTagPose", Blip24
        ).subscribe([], ntcore.PubSubOptions())

    def analyze(self, request: CompletedRequest, camera: CameraData) -> None:
        buffer: Mat = request.make_buffer("lores")  # type: ignore
        metadata: dict[str, Any] = request.get_metadata()

        y_len = camera.width * camera.height

        # truncate, ignore chrominance. this makes a view, very fast (300 ns)
        img = np.frombuffer(buffer, dtype=np.uint8, count=y_len)

        # this  makes a view, very fast (150 ns)
        img = img.reshape((camera.height, camera.width))
        # img = cv2.undistort(img, camera.mtx, camera.dist)

        # compute time since last frame
        current_time = time.time()
        total_et = current_time - camera.frame_time
        camera.frame_time = current_time

        fps: float = 1 / total_et

        camera.fps = fps
        camera.FPSPublisher.set(fps)

        # sensor timestamp is the boottime when the first byte was received from the sensor
        sensor_timestamp = metadata["SensorTimestamp"]
        # include all the work above in the latency
        system_time_ns = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        time_delta_ms = (system_time_ns - sensor_timestamp) // 1000000
        camera.LatencyPublisher.set(time_delta_ms)
        self.inst.flush()
        self.draw_text(img, f"fps {fps:.1f}", (5, 65))
        img_output = cv2.resize(img, (416, 308))
        camera.output_stream.putFrame(img_output) # type: ignore

    # these are white with black outline
    def draw_text(
        self, image: NDArray[np.uint8], msg: str, loc: tuple[int, int]
    ) -> None:
        cv2.putText(image, msg, loc, cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 6)
        cv2.putText(image, msg, loc, cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)


def getserial() -> str:
    with open("/proc/cpuinfo", "r", encoding="ascii") as cpuinfo:
        for line in cpuinfo:
            if line[0:6] == "Serial":
                return line[10:26]
    return ""


def main() -> None:
    print("main")
    print(Picamera2.global_camera_info()) # type: ignore
    camList: list[CameraData] = []
    if len(Picamera2.global_camera_info()) == 0: # type: ignore
        print("NO CAMERAS DETECTED, PLEASE TURN OFF PI AND CHECK CAMERA PORT(S)")
    for cameraData in Picamera2.global_camera_info(): # type: ignore
        camera = CameraData(cast(int, cameraData["Num"]))
        camList.append(camera)
    serial: str = getserial()
    print(serial)
    output = Test(serial, camList)
    try:
        while True:
            for camera in camList:
                request: CompletedRequest = camera.camera.capture_request() # type: ignore
                try:
                    output.analyze(request, camera)
                finally:
                    request.release()
    finally:
        for camera in camList:
            camera.camera.stop()


main()
