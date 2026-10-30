"""Account-based GTM for AI agents in private markets: Apollo -> research agent -> personas -> Saleshandy.

  python main.py demo                 sample accounts, no keys needed
  python main.py run                  research real firms, save briefs + CSV, send nothing
  python main.py run --accounts 3     research fewer firms (each costs Claude + web search)
  python main.py run --live           also add contacts to Saleshandy
  python main.py sequences | fields   look up Saleshandy IDs
"""
import argparse
import json
import os

import yaml
from dotenv import load_dotenv

from gtm import pipeline
from gtm.saleshandy import Saleshandy


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["demo", "run", "sequences", "fields"])
    parser.add_argument("--live", action="store_true", help="actually push contacts to Saleshandy")
    parser.add_argument("--accounts", type=int, default=5, help="max firms to research this run")
    parser.add_argument("--config", default="config/icp.yaml")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if args.command == "demo":
        pipeline.demo(config)
    elif args.command == "run":
        pipeline.run(config, live=args.live, accounts=args.accounts)
    else:
        client = Saleshandy(os.environ["SALESHANDY_API_KEY"])
        print(json.dumps(client.sequences() if args.command == "sequences" else client.fields(), indent=2))


if __name__ == "__main__":
    main()
