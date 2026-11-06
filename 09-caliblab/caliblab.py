"""CalibLab: fit a tool offset or register two coordinate frames."""
import argparse
import json
from pathlib import Path
from core import calibrate, save_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command')
    for mode in ['tcp', 'registration']:
        command = commands.add_parser(mode)
        command.add_argument('input', type=Path)
        command.add_argument('--output', type=Path, required=True)
        command.add_argument('--warning-mm', type=float, default=0.5)
    demo = commands.add_parser('demo')
    demo.add_argument('directory', type=Path)
    args = parser.parse_args()
    try:
        if args.command is None:
            from gui import launch
            launch()
        elif args.command == 'demo':
            from demo import generate
            generate(args.directory)
            for mode in ['tcp', 'registration']:
                report = calibrate(args.directory / (mode + '.csv'), mode)
                save_report(report, args.directory / (mode + '_report'))
            print('Generated synthetic measurements, truth and reports in', args.directory)
        else:
            report = calibrate(args.input, args.command, args.warning_mm)
            save_report(report, args.output)
            print(json.dumps({key: report[key] for key in ['mode', 'model', 'fit', 'held_out', 'warnings']}, indent=2))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()
