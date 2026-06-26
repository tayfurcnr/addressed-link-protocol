import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_generator_module():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "generate_message_registry.py"
    spec = importlib.util.spec_from_file_location("generate_message_registry", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GenerateMessageRegistryTests(unittest.TestCase):
    def test_duplicate_msg_id_is_rejected(self) -> None:
        module = load_generator_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            proto_dir = Path(temp_dir)
            (proto_dir / "one.proto").write_text(
                'syntax = "proto3";\n// ALP_MSG_ID: 0x0040\nmessage First {}\n',
                encoding="utf-8",
            )
            (proto_dir / "two.proto").write_text(
                'syntax = "proto3";\n// ALP_MSG_ID: 0x0040\nmessage Second {}\n',
                encoding="utf-8",
            )

            original_proto_dir = module.PROTO_DIR
            module.PROTO_DIR = proto_dir
            try:
                with self.assertRaises(ValueError):
                    module.collect_message_mappings()
            finally:
                module.PROTO_DIR = original_proto_dir

    def test_out_of_range_msg_id_is_rejected(self) -> None:
        module = load_generator_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            proto_dir = Path(temp_dir)
            (proto_dir / "bad.proto").write_text(
                'syntax = "proto3";\n// ALP_MSG_ID: 0x10000\nmessage TooLarge {}\n',
                encoding="utf-8",
            )

            original_proto_dir = module.PROTO_DIR
            module.PROTO_DIR = proto_dir
            try:
                with self.assertRaises(ValueError):
                    module.collect_message_mappings()
            finally:
                module.PROTO_DIR = original_proto_dir

    def test_multiple_proto_files_are_collected(self) -> None:
        module = load_generator_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            proto_dir = Path(temp_dir)
            (proto_dir / "alpha.proto").write_text(
                'syntax = "proto3";\n// ALP_MSG_ID: 0x0040\nmessage Alpha {}\n',
                encoding="utf-8",
            )
            (proto_dir / "beta.proto").write_text(
                'syntax = "proto3";\n// ALP_MSG_ID: 0x0041\nmessage Beta {}\n',
                encoding="utf-8",
            )

            original_proto_dir = module.PROTO_DIR
            module.PROTO_DIR = proto_dir
            try:
                mappings = module.collect_message_mappings()
            finally:
                module.PROTO_DIR = original_proto_dir

        self.assertEqual(
            mappings,
            [
                (0x0040, "alpha_pb2", "Alpha"),
                (0x0041, "beta_pb2", "Beta"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
