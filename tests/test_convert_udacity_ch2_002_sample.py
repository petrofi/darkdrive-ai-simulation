from __future__ import annotations

import unittest

from scripts.convert_udacity_ch2_002_sample import (
    evenly_spaced_indices,
    nearest_timestamp_index,
    parse_args,
)


class UdacityCh2002SampleConversionTests(unittest.TestCase):
    def test_evenly_spaced_indices_span_topic(self) -> None:
        indices = evenly_spaced_indices(1000, 5)
        self.assertEqual(indices, [1, 251, 501, 750, 1000])

    def test_evenly_spaced_indices_never_exceed_available_messages(self) -> None:
        self.assertEqual(evenly_spaced_indices(3, 10), [1, 2, 3])
        self.assertEqual(evenly_spaced_indices(0, 10), [])

    def test_nearest_timestamp_is_deterministic_and_prefers_earlier_on_tie(self) -> None:
        timestamps = [100, 200, 300]
        self.assertEqual(nearest_timestamp_index(timestamps, 250), 1)
        self.assertEqual(nearest_timestamp_index(timestamps, 290), 2)

    def test_cli_defaults_keep_sample_at_500_frames(self) -> None:
        args = parse_args([])
        self.assertEqual(args.frames_per_bag, 100)
        self.assertFalse(args.force)


if __name__ == "__main__":
    unittest.main()
