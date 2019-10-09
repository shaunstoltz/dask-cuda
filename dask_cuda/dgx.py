import os

from dask.distributed import SpecCluster

from .scheduler import Scheduler
from .utils import get_ucx_env
from .worker_spec import worker_spec


def DGX(
    interface=None,
    dashboard_address=":8787",
    threads_per_worker=1,
    silence_logs=True,
    CUDA_VISIBLE_DEVICES=None,
    protocol=None,
    enable_tcp_over_ucx=False,
    enable_infiniband=False,
    enable_nvlink=False,
    **kwargs,
):
    """ A Local Cluster for a DGX 1 machine

    NVIDIA's DGX-1 machine has a complex architecture mapping CPUs, GPUs, and
    network hardware.  This function creates a local cluster that tries to
    respect this hardware as much as possible.

    It creates one Dask worker process per GPU, and assigns each worker process
    the correct CPU cores and Network interface cards to maximize performance.
    If UCX and UCX-Py are also available, it's possible to use InfiniBand and
    NVLink connections for optimal data transfer performance.

    That being said, things aren't perfect.  Today a DGX has very high
    performance between certain sets of GPUs and not others.  A Dask DGX
    cluster that uses only certain tightly coupled parts of the computer will
    have significantly higher bandwidth than a deployment on the entire thing.

    Parameters
    ----------
    interface: str
        The external interface used to connect to the scheduler, usually
        the ethernet interface is used for connection (not the InfiniBand!).
    dashboard_address: str
        The address for the scheduler dashboard.  Defaults to ":8787".
    threads_per_worker: int
        Number of threads to be used for each CUDA worker process.
    silence_logs: bool
        Disable logging for all worker processes
    CUDA_VISIBLE_DEVICES: str
        String like ``"0,1,2,3"`` or ``[0, 1, 2, 3]`` to restrict activity to
        different GPUs
    protocol: str
        Protocol to use for communication, e.g., "tcp" or "ucx"
    enable_tcp_over_ucx: bool
        Set environment variables to enable TCP over UCX, even if InfiniBand
        and NVLink are not supported or disabled.
    enable_infiniband: bool
        Set environment variables to enable UCX InfiniBand support, requires
        protocol='ucx' and implies enable_tcp_over_ucx=True.
    enable_nvlink: bool
        Set environment variables to enable UCX NVLink support, requires
        protocol='ucx' and implies enable_tcp_over_ucx=True.

    Raises
    ------
    TypeError
        If enable_infiniband or enable_nvlink is True and protocol is not 'ucx'

    Examples
    --------
    >>> from dask_cuda import DGX
    >>> from dask.distributed import Client
    >>> cluster = DGX()
    >>> client = Client(cluster)
    """
    if (enable_infiniband or enable_nvlink) and protocol != "ucx":
        raise TypeError("Enabling InfiniBand or NVLink requires protocol='ucx'")

    ucx_net_devices = ""
    if enable_infiniband:
        ucx_net_devices = lambda i: "mlx5_%d:1" % (i // 2)

    spec = worker_spec(
        interface=interface,
        dashboard_address=dashboard_address,
        threads_per_worker=threads_per_worker,
        silence_logs=silence_logs,
        CUDA_VISIBLE_DEVICES=CUDA_VISIBLE_DEVICES,
        enable_tcp_over_ucx=enable_tcp_over_ucx,
        enable_infiniband=enable_infiniband,
        ucx_net_devices=ucx_net_devices,
        enable_nvlink=enable_nvlink,
        protocol=protocol,
        **kwargs,
    )

    ucx_env = get_ucx_env(
        interface=interface,
        enable_tcp=enable_tcp_over_ucx,
        enable_infiniband=enable_infiniband,
        enable_nvlink=enable_nvlink,
    )

    scheduler = {
        "cls": Scheduler,
        "options": {
            "interface": interface,
            "protocol": protocol,
            "dashboard_address": dashboard_address,
            "env": {**ucx_env},
        },
    }

    return SpecCluster(
        workers=spec, scheduler=scheduler, silence_logs=silence_logs, **kwargs
    )
