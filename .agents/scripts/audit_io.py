"""Atomic text exports for audit artifacts."""

import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def output_stream(path=None):
    if not path:
        yield sys.stdout
        return
    destination = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + destination.name + '.', dir=destination.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='') as stream:
            yield stream
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


@contextmanager
def database_lock(path):
    """Hold an OS-managed writer lock. A crashed process releases it automatically."""
    with open(str(path) + '.lock', 'a+b') as lock:
        try:
            if os.name == 'nt':
                import msvcrt
                lock.seek(0)
                if not lock.read(1):
                    lock.write(b'0')
                    lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise ValueError('another crawl process is using this database') from error
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
