"""Inherited Linux seccomp allowlist: browser IPC works, network sockets do not.

No socket(), connect(), io_uring, ptrace or descriptor acquisition from another
process is allowed. Only AF_UNIX socketpair() supports Chromium's internal IPC.
All unknown syscalls are denied, including future network entry points.
"""
import ctypes
import ctypes.util
import errno
import os
import socket
import sys

# Native Linux process, memory, filesystem and IPC operations required by headless Chromium.
ALLOWED = '''read write readv writev pread64 pwrite64 preadv pwritev preadv2 pwritev2
close close_range dup dup2 dup3 fcntl ioctl lseek stat fstat lstat newfstatat statx
access faccessat faccessat2 open openat openat2 getdents getdents64 readlink readlinkat
getcwd chdir fchdir mkdir mkdirat rmdir unlink unlinkat rename renameat renameat2
link linkat symlink symlinkat chmod fchmod fchmodat umask truncate ftruncate fallocate
fsync fdatasync sync_file_range statfs fstatfs utime utimes futimesat utimensat
mmap mprotect munmap mremap madvise mincore msync brk memfd_create membarrier
mlock munlock mlock2 mlockall munlockall
rt_sigaction rt_sigprocmask rt_sigreturn rt_sigpending rt_sigsuspend rt_sigtimedwait
sigaltstack signalfd signalfd4 kill tkill tgkill rt_tgsigqueueinfo
clone clone3 fork vfork execve execveat exit exit_group wait4 waitid
getpid getppid gettid getuid geteuid getgid getegid getresuid getresgid getgroups
setuid setgid setreuid setregid setresuid setresgid setgroups
setpgid getpgid getpgrp setsid getsid
futex futex_waitv set_robust_list get_robust_list set_tid_address rseq
prctl arch_prctl seccomp capget capset getrandom uname sysinfo
getrlimit setrlimit prlimit64 getrusage times time gettimeofday clock_gettime
clock_getres nanosleep clock_nanosleep alarm setitimer getitimer
sched_yield sched_getaffinity sched_setaffinity sched_getparam sched_setparam
sched_getscheduler sched_setscheduler sched_get_priority_min sched_get_priority_max
getpriority setpriority restart_syscall
pipe pipe2 poll ppoll select pselect6 epoll_create epoll_create1 epoll_ctl epoll_wait epoll_pwait epoll_pwait2
eventfd eventfd2 timerfd_create timerfd_settime timerfd_gettime
sendto recvfrom sendmsg recvmsg sendmmsg recvmmsg getsockopt setsockopt getsockname getpeername shutdown
fadvise64 readahead flock sendfile copy_file_range splice tee vmsplice
inotify_init inotify_init1 inotify_add_watch inotify_rm_watch
shmget shmat shmdt shmctl getcpu get_mempolicy set_mempolicy mbind
'''.split()


class Comparison(ctypes.Structure):
    _fields_ = [('arg', ctypes.c_uint), ('op', ctypes.c_uint),
                ('datum_a', ctypes.c_uint64), ('datum_b', ctypes.c_uint64)]


def restrict_network():
    if sys.platform != 'linux':
        raise ValueError('Linux seccomp is required')
    library = ctypes.util.find_library('seccomp')
    if not library:
        raise ValueError('libseccomp is required for browser network isolation')
    lib = ctypes.CDLL(library, use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_syscall_resolve_name.restype = ctypes.c_int
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Comparison)]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x00050000 | errno.EPERM)
    if not context:
        raise ValueError('cannot initialize seccomp')
    try:
        for name in ALLOWED:
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and lib.seccomp_rule_add_array(context, 0x7fff0000, number, 0, None) != 0:
                raise ValueError('cannot install browser syscall allowlist')
        pair = lib.seccomp_syscall_resolve_name(b'socketpair')
        comparison = Comparison(0, 4, socket.AF_UNIX, 0)
        if pair < 0 or lib.seccomp_rule_add_array(context, 0x7fff0000, pair, 1, ctypes.byref(comparison)) != 0:
            raise ValueError('cannot restrict browser IPC')
        if lib.seccomp_load(context) != 0:
            raise ValueError('kernel rejected browser seccomp filter')
    finally:
        lib.seccomp_release(context)


def probe():
    restrict_network()
    for family in (socket.AF_INET, socket.AF_INET6, socket.AF_UNIX):
        try:
            connection = socket.socket(family, socket.SOCK_STREAM)
        except PermissionError:
            continue
        connection.close()
        raise ValueError('socket isolation probe failed')
    a, b = socket.socketpair()
    a.send(b'isolated')
    assert b.recv(8) == b'isolated'
    a.close()
    b.close()
    print('seccomp-network-isolated')


if __name__ == '__main__':
    probe()
