import unittest
from pathlib import Path
from resolve_auto_organize import classify_media_clip

class TestResolveAutoOrganize(unittest.TestCase):

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
        self.assertIn("4K_UHD", cls["resolution_category"])
        self.assertIn("SlowMo_59fps", cls["resolution_category"])
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
        self.assertIn("1080p_FHD", cls["resolution_category"])
        self.assertIn("SlowMo_100fps", cls["resolution_category"])

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
        self.assertIn("Vertical", cls["resolution_category"])

if __name__ == "__main__":
    unittest.main()
