"""Successor qualification of chronology with preserved presentation priority."""
import argparse
import qualification as q
from chronology_priority import RecoveryChronologyMixin
import importlib.util
from pathlib import Path
_spec=importlib.util.spec_from_file_location('recovery_chronology_native',Path(__file__).with_name('qualify_native.py'))
qualify_native=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(qualify_native)

class Session(RecoveryChronologyMixin,q.previous.previous.Session):
    pass

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--version',default='002')
    q.Session=Session
    qualify_native.main(parser.parse_args().version)
