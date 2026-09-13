"""Offline tests. No API key, YouTube access, or media required."""
import argparse
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import collect_youtube as c

class CollectorTests(unittest.TestCase):
    def test_search_pagination_and_deduplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            queries = Path(tmp) / "queries.txt"
            queries.write_text("# heading\nblender test\n")
            client = Mock()
            client.get.side_effect = [
                {"items": [{"id": {"videoId": "A"}}], "nextPageToken": "next"},
                {"items": [{"id": {"videoId": "A"}}, {"id": {"videoId": "B"}}]}
            ]
            args = argparse.Namespace(queries=queries,start_query=0,limit_queries=1,
                pages=2,order="relevance",max_results=25,cc_only=True)
            result = c.search_ids(client, args)
            self.assertEqual(list(result), ["A", "B"])
            self.assertEqual(result["A"]["discovery_queries"], ["blender test"])
            self.assertEqual(client.get.call_args.kwargs["pageToken"], "next")
            self.assertEqual(client.get.call_args.kwargs["videoLicense"], "creativeCommon")

    def test_missing_video_removes_old_metadata(self):
        client = Mock()
        client.get.return_value = {"items": [{"id": "A", "snippet": {"title": "A"}}]}
        result = c.enrich(client, {"A": {"video_id": "A"},
                                  "B": {"video_id": "B", "youtube": {"old": True}}})
        self.assertEqual(result[0]["api_status"], "available")
        self.assertIsNone(result[1]["youtube"])
        self.assertEqual(result[1]["api_status"], "not_returned")
        self.assertEqual(result[0]["reuse_permission"], "not_established")

    def test_metadata_batches(self):
        client = Mock()
        client.get.return_value = {"items": []}
        rows = {str(i): {"video_id": str(i)} for i in range(51)}
        self.assertEqual(len(c.enrich(client, rows)), 51)
        self.assertEqual(client.get.call_count, 2)

    def test_channel_uploads(self):
        client = Mock()
        client.get.side_effect = [
            {"items": [{"contentDetails": {"relatedPlaylists": {"uploads": "UPLOADS"}}}]},
            {"items": [{"contentDetails": {"videoId": "A"}}], "nextPageToken": "next"},
            {"items": [{"contentDetails": {"videoId": "B"}}]}
        ]
        result = c.channel_ids(client, argparse.Namespace(channel_id="UCtest", pages=2))
        self.assertEqual(list(result), ["A", "B"])
        self.assertEqual(client.get.call_args.kwargs["playlistId"], "UPLOADS")

    def test_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rows.jsonl"
            rows = [{"video_id": "A", "text": "α"}]
            c.write_jsonl(path, rows)
            self.assertEqual(c.load_jsonl(path), rows)

    def test_query_bank_count_and_seed_status(self):
        root = Path(__file__).parent
        queries = [x for x in (root / "youtube_queries.txt").read_text().splitlines()
                   if x.strip() and not x.startswith("#")]
        self.assertEqual(len(queries), 48)
        self.assertEqual(len(set(queries)), 48)
        seeds = c.load_jsonl(root / "seed_candidates.jsonl")
        self.assertEqual(len(seeds), 8)
        for seed in seeds:
            self.assertEqual(seed["events"], [])
            self.assertEqual(seed["visual_review"], "not_performed")
        template = json.loads((root / "exemplar_template.json").read_text())
        self.assertFalse(template["validation"]["tested"])

if __name__ == "__main__":
    unittest.main()
