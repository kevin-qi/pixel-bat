import atexit
import hashlib
import json
import os
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager

# Network shares read at ~500 MB/s; the WSL ext4 filesystem reads at ~6 GB/s.
# Kilosort makes many full passes over the binary, so copying it to local disk
# once is a large win. Note /mnt/c is NOT a good target: the 9p passthrough
# caps it at ~240 MB/s, slower than the share itself.
DEFAULT_STAGE_DIR = os.environ.get(
    'PIXELBAT_STAGE_DIR', os.path.expanduser('~/.cache/pixelbat/stage')
)

_LOCKS = 'locks'

# A single SMB stream is latency-bound, so a serial copy leaves most of the
# link idle; several concurrent readers at different offsets recover it.
DEFAULT_WORKERS = 8
CHUNK_BYTES = 256 << 20


def _entry_key(src: str) -> str:
    """
    Identity of a staged copy: source path + size + mtime.

    Content hashing a 100 GB file is not viable, so identity is derived from
    metadata instead. Any change to the source yields a different key, so an
    outdated copy can never be mistaken for a current one -- it simply misses
    and gets reclaimed as an unreferenced entry.
    """
    st = os.stat(src)
    ident = f'{os.path.realpath(src)}|{st.st_size}|{st.st_mtime_ns}'
    return hashlib.sha256(ident.encode()).hexdigest()[:16]


def _alive(pid: int) -> bool:
    """Whether a process holding a lock still exists."""
    if pid <= 0:
        return False  # guard: os.kill(-1, 0) would signal every process
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, owned by someone else
    return True


def _live_lock_count(stage_dir: str, key: str) -> int:
    lock_dir = os.path.join(stage_dir, _LOCKS)
    if not os.path.isdir(lock_dir):
        return 0
    n = 0
    for name in os.listdir(lock_dir):
        entry_key, _, pid = name.rpartition('.')
        if entry_key != key:
            continue
        try:
            pid = int(pid)
        except ValueError:
            continue
        if _alive(pid):
            n += 1
        else:
            # Owner died (e.g. kernel restart) -- drop the stale lock.
            _quiet_remove(os.path.join(lock_dir, name))
    return n


def _quiet_remove(path: str) -> None:
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    except FileNotFoundError:
        pass


def _dir_size(path: str) -> int:
    return sum(
        os.path.getsize(os.path.join(path, f))
        for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f))
    )


def _partial_owner(partial: str) -> int:
    """Pid that was building this partial copy, or -1 if unknown."""
    try:
        with open(os.path.join(partial, 'meta.json')) as f:
            return int(json.load(f).get('pid', -1))
    except (OSError, ValueError, TypeError):
        return -1


def _write_meta(partial: str, src: str, size: int) -> None:
    with open(os.path.join(partial, 'meta.json'), 'w') as f:
        json.dump({'source': src, 'size': size,
                   'mtime_ns': os.stat(src).st_mtime_ns,
                   'boot_id': _boot_id(), 'chunk_bytes': CHUNK_BYTES,
                   'pid': os.getpid()}, f, indent=1)


def _adopt_partial(partial: str, size: int, verbose: bool = True) -> set:
    """
    Return the chunks already copied into `partial`, or an empty set if it
    cannot be trusted. The source key already pins size and mtime, so the
    only remaining risks are a concurrent writer, a layout change, or a
    reboot -- each of which is checked here.
    """
    if not os.path.isdir(partial):
        return set()

    owner = _partial_owner(partial)
    if owner != os.getpid() and _alive(owner):
        raise IOError(f'pid {owner} is already staging this file; '
                      f'wait for it to finish or kill it.')

    try:
        with open(os.path.join(partial, 'meta.json')) as f:
            meta = json.load(f)
    except (OSError, ValueError):
        meta = {}

    if (meta.get('boot_id') != _boot_id()
            or meta.get('chunk_bytes') != CHUNK_BYTES
            or meta.get('size') != size):
        if verbose:
            print('[stage] discarding partial copy (stale layout or pre-reboot)')
        _quiet_remove(partial)
        return set()

    done = set()
    try:
        with open(os.path.join(partial, 'progress')) as f:
            for line in f:
                line = line.strip()
                if line.isdigit():
                    done.add(int(line))
    except OSError:
        pass
    if done and verbose:
        print(f'[stage] resuming: {len(done) * CHUNK_BYTES / 1e9:.1f} GB already copied')
    return done


def _reclaim(stage_dir: str, protect_key: str = None, max_entries: int = 1,
             verbose: bool = True) -> None:
    """
    Remove staged copies that are not protected, not in use, and beyond the
    entry budget. This runs on every acquire, which is what makes cleanup
    robust: even if a kernel is killed and no teardown ever runs, the next
    call reclaims whatever it orphaned.
    """
    if not os.path.isdir(stage_dir):
        return

    complete, partial = [], []
    for name in os.listdir(stage_dir):
        path = os.path.join(stage_dir, name)
        if name == _LOCKS or not os.path.isdir(path):
            continue
        (partial if name.endswith('.partial') else complete).append(name)

    # In-progress copies: keep the one we are about to resume and any owned
    # by a live process; the rest are garbage from abandoned runs.
    for name in partial:
        if protect_key and name == f'{protect_key}.partial':
            continue
        if _alive(_partial_owner(os.path.join(stage_dir, name))):
            continue
        if verbose:
            print(f'[stage] discarding abandoned copy: {name}')
        _quiet_remove(os.path.join(stage_dir, name))

    # Newest first; the protected key never counts against the budget.
    complete.sort(key=lambda n: os.path.getmtime(os.path.join(stage_dir, n)),
                  reverse=True)
    allowance = max_entries - 1 if protect_key else max_entries

    for name in complete:
        if name == protect_key:
            continue
        if allowance > 0:
            allowance -= 1
            continue
        if _live_lock_count(stage_dir, name):
            if verbose:
                print(f'[stage] keeping {name}: in use by another process')
            continue
        if verbose:
            freed = _dir_size(os.path.join(stage_dir, name)) / 1e9
            print(f'[stage] evicting {name} ({freed:.1f} GB)')
        _quiet_remove(os.path.join(stage_dir, name))


def _boot_id() -> str:
    """
    Identifies the current boot. Resuming a partial copy is only safe within
    one boot: a killed process leaves its written pages in the page cache and
    the kernel still flushes them, but a machine crash may not have. If the
    boot id changed, the partial is discarded rather than trusted.
    """
    try:
        with open('/proc/sys/kernel/random/boot_id') as f:
            return f.read().strip()
    except OSError:
        return ''


def _copy(src: str, dst: str, size: int, progress_path: str, done: set,
          workers: int = DEFAULT_WORKERS, verbose: bool = True) -> None:
    """
    Copy `src` to `dst` using `workers` concurrent readers, skipping chunks
    already recorded in `done`. Each completed chunk is appended to
    `progress_path`, so an interrupted copy resumes instead of restarting.
    """
    n_chunks = (size + CHUNK_BYTES - 1) // CHUNK_BYTES
    todo = [i for i in range(n_chunks) if i not in done]
    if not todo:
        return

    fd = os.open(dst, os.O_WRONLY | os.O_CREAT)
    os.ftruncate(fd, size)

    state = {'bytes': len(done) * CHUNK_BYTES, 'next': 0.0}
    lock = threading.Lock()
    t0 = time.time()
    prog = open(progress_path, 'a')

    def copy_chunk(i):
        off = i * CHUNK_BYTES
        want = min(CHUNK_BYTES, size - off)
        got = 0
        with open(src, 'rb') as fin:
            fin.seek(off)
            while got < want:
                buf = fin.read(min(8 << 20, want - got))
                if not buf:
                    raise IOError(f'Short read at offset {off + got} of {src}')
                os.pwrite(fd, buf, off + got)
                got += len(buf)
        with lock:
            prog.write(f'{i}\n')
            prog.flush()
            state['bytes'] += want
            frac = state['bytes'] / size
            if verbose and frac >= state['next']:
                rate = (state['bytes'] - len(done) * CHUNK_BYTES) / (time.time() - t0) / 1e6
                print(f'[stage]   {state["bytes"] / 1e9:6.1f} / {size / 1e9:.1f} GB '
                      f'({frac:4.0%}, {rate:.0f} MB/s)')
                state['next'] = frac + 0.05

    try:
        with ThreadPoolExecutor(workers) as ex:
            for _ in ex.map(copy_chunk, todo):
                pass
        os.fsync(fd)
    finally:
        prog.close()
        os.close(fd)

    if os.path.getsize(dst) != size:
        raise IOError(f'Staged copy is {os.path.getsize(dst)} bytes, expected {size}')


@contextmanager
def stage_file(src: str, stage_dir: str = None, keep: bool = True,
               max_entries: int = 1, workers: int = DEFAULT_WORKERS,
               verbose: bool = True):
    """
    Yield a fast local path for `src`, copying it to local disk if needed.

    Reruns reuse an existing copy, so only the first run pays the copy cost.
    An interrupted copy resumes where it stopped. At most `max_entries` copies
    exist at any time -- staging a different file evicts the previous one --
    so repeated use cannot accumulate stale data.

    Args:
        src: File on slow storage (e.g. a network share)
        stage_dir: Cache root; must be on fast local disk. Defaults to
            $PIXELBAT_STAGE_DIR or ~/.cache/pixelbat/stage
        keep: Leave the copy in place on exit so the next run is instant.
            Set False to delete it as soon as the block ends.
        max_entries: How many staged copies to retain
        workers: Concurrent readers. A single SMB stream is latency-bound,
            so several offsets in flight read faster than one.
        verbose: Print copy progress and cleanup actions

    Yields:
        Path to the local copy

    Example:
        with stage_file(binary_file) as local_binary:
            run_kilosort(filename=local_binary, ...)
    """
    stage_dir = stage_dir or DEFAULT_STAGE_DIR
    src = os.path.realpath(src)
    key = _entry_key(src)
    size = os.path.getsize(src)

    lock_dir = os.path.join(stage_dir, _LOCKS)
    os.makedirs(lock_dir, exist_ok=True)

    # Claim the entry before touching the cache, so a concurrent sweep cannot
    # evict what we are about to use or build.
    lock = os.path.join(lock_dir, f'{key}.{os.getpid()}')
    open(lock, 'w').close()
    release = lambda: _quiet_remove(lock)
    atexit.register(release)

    try:
        _reclaim(stage_dir, protect_key=key, max_entries=max_entries, verbose=verbose)

        entry = os.path.join(stage_dir, key)
        local = os.path.join(entry, os.path.basename(src))

        if os.path.exists(local) and os.path.getsize(local) == size:
            if verbose:
                print(f'[stage] reusing local copy: {local}')
        else:
            free = shutil.disk_usage(stage_dir).free
            if free < size * 1.05:
                raise IOError(
                    f'Need {size / 1e9:.1f} GB to stage {os.path.basename(src)}, '
                    f'only {free / 1e9:.1f} GB free on {stage_dir}. '
                    f'Free space or pass a different stage_dir.'
                )

            # Build in a partial directory, then publish with an atomic
            # rename, so a visible entry is always a complete copy. The
            # partial name is stable (no pid) so an interrupted copy can be
            # adopted and resumed instead of restarted.
            partial = os.path.join(stage_dir, f'{key}.partial')
            done = _adopt_partial(partial, size, verbose)
            os.makedirs(partial, exist_ok=True)
            _write_meta(partial, src, size)

            if verbose:
                print(f'[stage] copying {size / 1e9:.1f} GB {src} -> {stage_dir}')
            _copy(src, os.path.join(partial, os.path.basename(src)), size,
                  os.path.join(partial, 'progress'), done, workers, verbose)
            try:
                os.replace(partial, entry)
            except OSError:
                # Another process published the same key first; theirs is
                # equivalent, so drop ours.
                _quiet_remove(partial)

            if verbose:
                print(f'[stage] ready: {local}')

        yield local

    finally:
        release()
        atexit.unregister(release)
        if not keep and not _live_lock_count(stage_dir, key):
            if verbose:
                print(f'[stage] removing {key}')
            _quiet_remove(os.path.join(stage_dir, key))
            _quiet_remove(os.path.join(stage_dir, f'{key}.partial'))


def stage_status(stage_dir: str = None, verbose: bool = True) -> list:
    """Report what is currently staged. Returns a list of entry dicts."""
    stage_dir = stage_dir or DEFAULT_STAGE_DIR
    out = []
    if os.path.isdir(stage_dir):
        for name in sorted(os.listdir(stage_dir)):
            path = os.path.join(stage_dir, name)
            if name == _LOCKS or not os.path.isdir(path):
                continue
            info = {'key': name, 'gb': _dir_size(path) / 1e9,
                    'in_use': bool(_live_lock_count(stage_dir, name)), 'source': None}
            try:
                with open(os.path.join(path, 'meta.json')) as f:
                    info['source'] = json.load(f)['source']
            except (FileNotFoundError, ValueError, KeyError):
                pass
            out.append(info)

    if verbose:
        if not out:
            print(f'[stage] nothing staged in {stage_dir}')
        for e in out:
            print(f"[stage] {e['key']}  {e['gb']:6.1f} GB  "
                  f"{'in use' if e['in_use'] else 'idle  '}  {e['source']}")
        if out:
            free = shutil.disk_usage(stage_dir).free / 1e9
            print(f'[stage] {free:.1f} GB free on {stage_dir}')
    return out


def purge_stage(stage_dir: str = None, verbose: bool = True) -> None:
    """Remove every staged copy that no live process is using."""
    _reclaim(stage_dir or DEFAULT_STAGE_DIR, protect_key=None, max_entries=0,
             verbose=verbose)
