"""SCA2 protocol CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .protocol import load_protocol, repo_root
from .runs import format_receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sca2",
        description="Run a frozen SCA2 protocol. The protocol file is the scientific object.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    label = sub.add_parser("label", help="Sign-relabel the shared A/B bank for every protocol country")
    label.add_argument("--protocol", type=Path, required=True)
    label.add_argument("--output-dir", type=Path, default=None)
    label.add_argument("--runs-root", type=Path, default=None)

    show = sub.add_parser("show", help="Print protocol name, hash, and wiring status")
    show.add_argument("--protocol", type=Path, required=True)

    generate = sub.add_parser(
        "generate",
        help="Inspect the frozen A/B bank (does not call teacher/generator)",
    )
    generate.add_argument("--protocol", type=Path, required=True)
    generate.add_argument("--runs-root", type=Path, default=None)
    generate.add_argument(
        "--materialize",
        action="store_true",
        help="Refuse by design: a new bank is a new protocol, not a flag.",
    )

    train = sub.add_parser("train", help="Freeze a DPO/QLoRA plan (does not launch GPU)")
    train.add_argument("--protocol", type=Path, required=True)
    train.add_argument("--runs-root", type=Path, default=None)
    train.add_argument("--data-dir", type=Path, default=None)
    train.add_argument("--countries", nargs="+", default=None)
    train.add_argument(
        "--execute",
        action="store_true",
        help="Refuse by design until a local trainer is wired.",
    )

    eval_cmd = sub.add_parser("eval", help="WVS / placebos (not wired)")
    eval_cmd.add_argument("--protocol", type=Path, required=True)

    return parser


def _not_wired(command: str, protocol_path: Path) -> int:
    protocol = load_protocol(protocol_path)
    print(
        format_receipt(
            {
                "run_id": None,
                "stage": command,
                "status": "not_wired",
                "protocol_name": protocol["name"],
                "protocol_hash": protocol["_hash"],
            }
        )
    )
    print(f"ok=false  {command} is declared in the protocol and not implemented in the CLI yet")
    return 2


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "show":
        protocol = load_protocol(args.protocol)
        print(
            format_receipt(
                {
                    "run_id": None,
                    "stage": "show",
                    "status": protocol.get("status"),
                    "protocol_name": protocol["name"],
                    "protocol_hash": protocol["_hash"],
                }
            )
        )
        print(f"root      {repo_root()}")
        print(f"labeling  {protocol['generation'].get('labeling')}")
        print(f"train     wired={protocol['train'].get('wired')}")
        print(f"eval      wired={protocol['eval'].get('wired')}")
        return 0
    if args.command == "label":
        from .label import run_label

        run_label(args.protocol, output_dir=args.output_dir, runs_root=args.runs_root)
        return 0
    if args.command == "generate":
        from .generate import run_generate

        try:
            receipt = run_generate(
                args.protocol,
                materialize=args.materialize,
                runs_root=args.runs_root,
            )
        except RuntimeError as exc:
            print(f"ok=false  {exc}")
            return 2
        return 0 if receipt.get("status") == "bank_reused" else 1
    if args.command == "train":
        from .train import run_train

        try:
            receipt = run_train(
                args.protocol,
                countries=args.countries,
                data_dir=args.data_dir,
                execute=args.execute,
                runs_root=args.runs_root,
            )
        except (RuntimeError, FileNotFoundError) as exc:
            print(f"ok=false  {exc}")
            return 2
        return 0 if receipt.get("status") == "planned" else 1
    return _not_wired(args.command, args.protocol)


if __name__ == "__main__":
    raise SystemExit(main())
