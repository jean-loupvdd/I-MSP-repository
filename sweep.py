# sweep.py

import os
import time
import numpy as np
import tifffile
from camera_capture import CameraCapture

def wavelength_sweep(
        mono,
        start_wl,
        end_wl,
        step_wl=10,
        output_dir="captures",
        delay_after_move=5.0,
        bit_mode="12bit",
        n_avg_frames=16,
        on_step=None,
        on_error=None,
    ):
    """
    Sweep de monochromator en neem beelden op.
    Geen prints; fouten worden doorgegeven via on_error callback.
    """

    os.makedirs(output_dir, exist_ok=True)

    wl_min, wl_max = sorted([start_wl, end_wl])
    wavelengths = np.arange(wl_min, wl_max + step_wl, step_wl)

    images_np = []
    stored_wl = []

    try:
        with CameraCapture(output_dir) as camcap:
            for wl in wavelengths:

                if not mono.set_wavelength(wl):
                    if on_error:
                        on_error(f"Golflengte {wl} nm kon niet worden ingesteld.")
                    continue

                if on_step:
                    on_step(wl)

                time.sleep(delay_after_move)

                # --- Capture ---
                if bit_mode.lower() == "16bit":
                    img = combine_frames_to_16bit(camcap, n_frames=n_avg_frames)
                else:
                    img = camcap.capture_frame_as_numpy()

                tifffile.imwrite(os.path.join(output_dir, f"wl_{int(wl)}nm.tiff"), img)

                images_np.append(img)
                stored_wl.append(float(wl))

    except Exception as e:
        if on_error:
            on_error(f"Sweep fout: {e}")
        return

    # --- Save combined TIFF ---
    if images_np:
        stack = np.stack(images_np)
        tifffile.imwrite(
            os.path.join(output_dir, "alles_in_een_sweep.tiff"),
            stack,
            metadata={"wavelengths": stored_wl}
        )
    else:
        if on_error:
            on_error("Geen beelden opgeslagen.")

def combine_frames_to_16bit(camcap, n_frames=16):
    """Combineer meerdere 12-bit frames tot één 16-bit frame."""
    frames = camcap.capture_sequence_as_numpy(n_frames)
    frames = [f.astype(np.uint16) for f in frames]
    summed = np.sum(frames, axis=0)
    return np.clip(summed, 0, 65535).astype(np.uint16)
