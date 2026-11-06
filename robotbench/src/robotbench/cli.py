"""RobotBench command line. Failure/cancellation results are still saved."""
import argparse
import json
from pathlib import Path
from . import __version__
from .engine import run_experiment
from .experiment import load_experiment
from .results import atomic_json,load_run,export_csv,compare_runs
from .workspace import initialize,save_workspace_run


def main(argv=None):
    parser=argparse.ArgumentParser(prog='robotbench',description='Build, run and debug reproducible robot experiments.')
    parser.add_argument('--version',action='version',version=__version__)
    commands=parser.add_subparsers(dest='command')
    init=commands.add_parser('init',help='Create a workspace with bundled robot and experiments');init.add_argument('directory',type=Path)
    run=commands.add_parser('run',help='Run an experiment and save its complete result');run.add_argument('experiment',type=Path);run.add_argument('--output',type=Path);run.add_argument('--csv',type=Path)
    inspect=commands.add_parser('inspect',help='Inspect a saved run');inspect.add_argument('run',type=Path)
    compare=commands.add_parser('compare',help='Compare a baseline run with a current run');compare.add_argument('baseline',type=Path);compare.add_argument('current',type=Path);compare.add_argument('--output',type=Path)
    gui=commands.add_parser('gui',help='Open the desktop workspace');gui.add_argument('workspace',nargs='?',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=='init':
            print('Created workspace:',initialize(args.directory));return 0
        if args.command=='run':
            config,robot=load_experiment(args.experiment);result=run_experiment(config,robot)
            if args.output:atomic_json(args.output,result);path=args.output
            else:path=save_workspace_run(args.experiment.parent,result)
            if args.csv:export_csv(result,args.csv)
            print(json.dumps({'saved_run':str(path),'status':result['status'],'failure_reason':result['failure_reason'],'metrics':result['metrics']},indent=2))
            return 0 if result['status']=='completed' else 1
        if args.command=='inspect':
            result=load_run(args.run);print(json.dumps({k:result[k] for k in ['run_id','status','failure_reason','metrics','events']},indent=2));return 0
        if args.command=='compare':
            result=compare_runs(load_run(args.baseline),load_run(args.current))
            if args.output:atomic_json(args.output,result)
            print(json.dumps(result,indent=2));return 0
        from .gui import launch
        launch(getattr(args,'workspace',None));return 0
    except (OSError,ValueError,TypeError) as exc:
        parser.error(str(exc))
    except KeyboardInterrupt:
        return 130


if __name__=='__main__':raise SystemExit(main())
