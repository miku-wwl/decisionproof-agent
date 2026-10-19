import argparse
import getpass
import json
from pathlib import Path

from .service import provision


def main():
    parser = argparse.ArgumentParser(description="DecisionProof offline sandbox; no live sponsors or device changes")
    commands = parser.add_subparsers(dest="command",required=True)
    init = commands.add_parser("init",help="Create a fresh sandbox, never reset history")
    init.add_argument("--directory",type=Path,required=True)
    serve = commands.add_parser("serve",help="Serve authenticated localhost UI with one runtime owner")
    serve.add_argument("--directory",type=Path,required=True)
    serve.add_argument("--port",type=int,default=8765)
    serve.add_argument("--predecessor-stopped",action="store_true",help="Operator attests the previous sandbox process has stopped")
    args = parser.parse_args()
    if args.command == "init":
        provision(args.directory,getpass.getpass("Unique local sandbox password (12+ characters): "))
        print("Fresh sandbox initialized; password and capability were not printed")
    else:
        import uvicorn
        from .web import create_app
        uvicorn.run(create_app(args.directory,origin=f"http://127.0.0.1:{args.port}",predecessor_stopped=args.predecessor_stopped),
                    host="127.0.0.1",port=args.port,workers=1,access_log=False)


if __name__ == "__main__":
    main()
