import argparse

from src.pm.pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True, help="Path to bundle JSON")
    parser.add_argument("--policy", required=True, help="Path to policy YAML")
    args = parser.parse_args()

    final_state = run_pipeline(
        bundle_path=args.bundle,
        policy_path=args.policy,
    )

    print(f"Run complete: {final_state['out_dir']}")

    if "trace" in final_state:
        print("Execution trace:", final_state["trace"])


if __name__ == "__main__":
    main()