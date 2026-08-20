import unittest
import sys
from pathlib import Path

# Add current directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from resolve_auto_organize import classify_media_clip, get_strict_resolution_label, get_normalized_fps_label

class TestResolveAutoOrganize(unittest.TestCase):

    def test_strict_resolution_labels(self):
        # 16:9 standards
        self.assertEqual(get_strict_resolution_label(1920, 1080), "1080p_FHD")
        self.assertEqual(get_strict_resolution_label(3840, 2160), "4K_UHD_3840x2160")
        self.assertEqual(get_strict_resolution_label(5464, 3070), "5.4K_5464x3070")
        self.assertEqual(get_strict_resolution_label(4096, 2160), "DCI_4K_4096x2160")
        self.assertEqual(get_strict_resolution_label(1280, 720), "720p_HD")

        # 4:3 Photo Sensor Ratios
        self.assertEqual(get_strict_resolution_label(4032, 3024), "Photo_4x3_4032x3024")
        self.assertEqual(get_strict_resolution_label(4000, 3000), "Photo_4x3_4000x3000")

        # Vertical
        self.assertEqual(get_strict_resolution_label(3024, 4032), "Vertical_3024x4032")
        self.assertEqual(get_strict_resolution_label(1080, 1920), "Vertical_1080x1920")

    def test_normalized_fps_labels(self):
        self.assertEqual(get_normalized_fps_label(23.976), "24fps")
        self.assertEqual(get_normalized_fps_label(25.0), "25fps")
        self.assertEqual(get_normalized_fps_label(29.97), "30fps")
        self.assertEqual(get_normalized_fps_label(50.0), "50fps_SlowMo")
        self.assertEqual(get_normalized_fps_label(59.94), "60fps_SlowMo")
        self.assertEqual(get_normalized_fps_label(100.0), "100fps_SlowMo")
        self.assertEqual(get_normalized_fps_label(240.0), "240fps_SlowMo")

    def test_classify_dji_drone(self):
        meta = {
            "filename": "2019-07-22__DJI_0011.MP4",
            "make": "DJI",
            "model": "FC6310",
            "handler": ".DJI.Meta",
            "major_brand": "avc1",
            "comment": "DE=TrueColor",
            "width": 3840,
            "height": 2160,
            "fps": 59.94,
            "bit_depth": 8,
            "color_transfer": "",
        }
        cls = classify_media_clip(meta)
        self.assertEqual(cls["camera_type"], "DJI")
        self.assertEqual(cls["clip_color"], "Orange")
        self.assertEqual(cls["resolution_category"], "4K_UHD_3840x2160")
        self.assertEqual(cls["fps_label"], "60fps_SlowMo")
        self.assertEqual(cls["cst_profile"], "DJI D-Cinelike -> Rec.709")

    def test_classify_sony_xavc_slowmo(self):
        meta = {
            "filename": "2021-01-01__videos__C0028.mov",
            "make": "Sony",
            "model": "ILCE-7M3",
            "handler": "",
            "major_brand": "XAVC",
            "comment": "",
            "width": 1920,
            "height": 1080,
            "fps": 100.0,
            "bit_depth": 8,
            "color_transfer": "",
        }
        cls = classify_media_clip(meta)
        self.assertEqual(cls["camera_type"], "Sony")
        self.assertEqual(cls["clip_color"], "Teal")
        self.assertEqual(cls["resolution_category"], "1080p_FHD")
        self.assertEqual(cls["fps_label"], "100fps_SlowMo")

    def test_classify_panasonic_s5_vlog(self):
        meta = {
            "filename": "2024-03-29__P1017964.MP4",
            "make": "Panasonic",
            "model": "DC-S5",
            "handler": "Panasonic Static Metadata",
            "major_brand": "mp42",
            "comment": "",
            "width": 3840,
            "height": 2160,
            "fps": 25.0,
            "bit_depth": 10,
            "color_transfer": "v-log",
        }
        cls = classify_media_clip(meta)
        self.assertEqual(cls["camera_type"], "Panasonic")
        self.assertEqual(cls["clip_color"], "Yellow")
        self.assertEqual(cls["cst_profile"], "Panasonic V-Gamut / V-Log")

    def test_classify_vertical_timelapse(self):
        meta = {
            "filename": "2023-05-28__TL portrait.mp4",
            "make": "",
            "model": "",
            "handler": "",
            "major_brand": "isom",
            "comment": "",
            "width": 3024,
            "height": 4032,
            "fps": 29.97,
            "bit_depth": 8,
            "color_transfer": "",
        }
        cls = classify_media_clip(meta)
        self.assertEqual(cls["camera_type"], "Timelapse")
        self.assertEqual(cls["clip_color"], "Blue")
        self.assertEqual(cls["resolution_category"], "Vertical_3024x4032")
        self.assertEqual(cls["fps_label"], "30fps")

if __name__ == "__main__":
    unittest.main()
