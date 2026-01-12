# camera_capture.py

from vimba import Vimba, PixelFormat, FrameStatus
import os
import time
import cv2  

class CameraCapture:
    """
    Camera-capture klasse voor single-frame en multi-frame opnames.
    Geen print-statements; fouten worden als exceptions gegooid.
    """
    def __init__(self, output_dir="captures"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        self.vimba = None
        self.cam = None
        self.features = None

    def __enter__(self):
        self.vimba = Vimba.get_instance()
        self.vimba.__enter__()

        cams = self.vimba.get_all_cameras()
        if not cams:
            raise RuntimeError("Geen camera gevonden!")

        self.cam = cams[0]
        self.cam.__enter__()

        # Cache features
        self.features = {f.get_name() for f in self.cam.get_all_features()}

        # Pixel format
        if "PixelFormat" in self.features:
            self.cam.set_pixel_format(PixelFormat.Mono12)

        # Gain
        if "GainAuto" in self.features:
            self.cam.get_feature_by_name("GainAuto").set("Off")
        if "Gain" in self.features:
            self.cam.get_feature_by_name("Gain").set(0)
            
        # Exposure
        if "ExposureAuto" in self.features:
            self.cam.get_feature_by_name("ExposureAuto").set("Off")
        if "ExposureTimeAbs" in self.features:
            self.cam.get_feature_by_name("ExposureTimeAbs").set(1)  # 1 ms

        # Black level
        if "BlackLevel" in self.features:
            self.cam.get_feature_by_name("BlackLevel").set(0)

        return self

    def capture_frame_as_numpy(self, timeout_ms=2500):
        """Neem één frame op zonder recursion-loop."""
        if not self.cam:
            raise RuntimeError("Camera niet geïnitialiseerd")

        start = time.time()
        while True:
            frame = self.cam.get_frame(timeout_ms=timeout_ms)
            if frame.get_status() == FrameStatus.Complete:
                return frame.as_numpy_ndarray()

            if (time.time() - start) * 1000 > timeout_ms:
                raise TimeoutError("Frame capture timeout")

    def capture_sequence_as_numpy(self, n_frames=16, timeout_ms=3000):
        """Neem meerdere frames op en retourneer als numpy arrays."""
        if not self.cam:
            raise RuntimeError("Camera niet geïnitialiseerd")

        frames = []
        self.cam.start_capture()

        try:
            with self.cam.get_frame_generator(limit=n_frames, timeout_ms=timeout_ms) as gen:
                for frame in gen:
                    frame.wait_for_capture()
                    frames.append(frame.as_numpy_ndarray())
        finally:
            self.cam.stop_capture()

        return frames

    def save_frame(self, filename):
        img = self.capture_frame_as_numpy()
        cv2.imwrite(os.path.join(self.output_dir, filename), img)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Fout-veilig afsluiten
        try:
            if self.cam:
                self.cam.__exit__(exc_type, exc_val, exc_tb)
        finally:
            if self.vimba:
                self.vimba.__exit__(exc_type, exc_val, exc_tb)
