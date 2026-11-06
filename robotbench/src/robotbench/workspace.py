"""Workspace setup and run discovery; all resources are bundled locally."""
from datetime import datetime,timezone
from importlib.resources import files
from pathlib import Path
import shutil
from .results import atomic_json


def initialize(directory):
    directory=Path(directory)
    if directory.exists() and any(directory.iterdir()):raise ValueError('Choose an empty or new workspace directory')
    directory.mkdir(parents=True,exist_ok=True)
    resource=files('robotbench').joinpath('resources')
    for item in resource.iterdir():
        if item.name.endswith(('.urdf','.json')):(directory/item.name).write_text(item.read_text(encoding='utf-8'),encoding='utf-8')
    (directory/'runs').mkdir(exist_ok=True)
    return directory


def save_workspace_run(workspace,run):
    name=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+run['run_id'][:8]+'.run.json'
    path=Path(workspace)/'runs'/name
    atomic_json(path,run)
    return path


def discover_runs(workspace):
    return sorted((Path(workspace)/'runs').glob('*.run.json'),reverse=True)
