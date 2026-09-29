"""
Unit tests verifying clean, database-agnostic module imports.
Ensures ML runtime modules can be imported without credentials, network access, or side effects.
"""

import os
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class TestModuleImports(unittest.TestCase):
    def setUp(self):
        # Save and wipe any Supabase credentials from environment
        self._saved_env = {}
        for key in ["SUPABASE_URL", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_ANON_KEY"]:
            if key in os.environ:
                self._saved_env[key] = os.environ.pop(key)

    def tearDown(self):
        # Restore environment
        for key, val in self._saved_env.items():
            os.environ[key] = val

    def test_import_waste_status_service_no_credentials(self):
        """Verify ML.waste.waste_status_service imports cleanly without credentials."""
        from ML.waste.waste_status_service import WasteStatusEngine, WasteStatusResult

        engine = WasteStatusEngine()
        self.assertEqual(engine.warning_threshold, 70.0)
        self.assertEqual(engine.critical_threshold, 85.0)
        self.assertEqual(engine.overflow_threshold, 100.0)
        self.assertEqual(engine.surge_threshold, 15.0)

    def test_import_forecast_service_no_credentials(self):
        """Verify ML.forecasting.forecast_service imports cleanly without credentials."""
        from ML.forecasting.forecast_service import (
            SENSOR_CONFIGS,
            get_sensor_config,
            train_and_forecast,
            validate_forecast,
        )

        self.assertEqual(len(SENSOR_CONFIGS), 5)
        cfg = get_sensor_config("SEN-023")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg["facility_id"], "FAC-10")
        self.assertTrue(callable(train_and_forecast))
        self.assertTrue(callable(validate_forecast))

    def test_root_ml_package_exports(self):
        """Verify ML package exports canonical symbols."""
        import ML

        self.assertTrue(hasattr(ML, "WasteStatusEngine"))
        self.assertTrue(hasattr(ML, "WasteStatusResult"))
        self.assertTrue(hasattr(ML, "SENSOR_CONFIGS"))
        self.assertTrue(hasattr(ML, "train_and_forecast"))

    def test_no_supabase_in_ml_modules(self):
        """Verify ML modules do not import or reference Supabase client modules."""
        import ML.forecasting.forecast_service as fs
        import ML.waste.waste_status_service as ws

        for mod in [fs, ws]:
            self.assertFalse(hasattr(mod, "create_client"), f"{mod.__name__} has create_client!")
            self.assertFalse(hasattr(mod, "supabase"), f"{mod.__name__} has supabase!")


if __name__ == "__main__":
    unittest.main()
