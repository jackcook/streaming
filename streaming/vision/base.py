# Copyright 2023 MosaicML Streaming authors
# SPDX-License-Identifier: Apache-2.0

"""Base classes for computer vision :class:`StreamingDataset`s."""

from typing import Any, Callable, Optional, Tuple

from torchvision.datasets import VisionDataset
from torchvision.transforms.functional import to_tensor

from streaming.base import StreamingDataset

__all__ = ['StreamingVisionDataset']


class StandardTransform:
    """Individual input and output transforms called jointly, following torchvision.

    Args:
        transform (Callable, optional): Input transform. Defaults to ``None``.
        target_transform (Callable, optional): Output transform. Defaults to ``None``.
    """

    def __init__(self,
                 transform: Optional[Callable] = None,
                 target_transform: Optional[Callable] = None) -> None:
        self.transform = transform
        self.target_transform = target_transform

    def __call__(self, x: Any, y: Any) -> Tuple[Any, Any]:
        """Apply the transforms to input and output.

        Args:
            x (Any): Input.
            y (Any): Output.

        Returns:
            Tuple[Any, Any]: Transformed input and output.
        """
        if self.transform:
            x = self.transform(x)
        else:
            x = to_tensor(x)
        if self.target_transform:
            y = self.target_transform(y)
        return x, y


class StreamingVisionDataset(StreamingDataset, VisionDataset):
    """A streaming, iterable, torchvision VisionDataset.

    Args:
        remote (str, optional): Remote path or directory to download the dataset from. If ``None``,
            its data must exist locally. StreamingDataset uses either ``streams`` or
            ``remote``/``local``. Defaults to ``None``.
        local (str, optional): Local working directory to download shards to. This is where shards
            are cached while they are being used. Uses a temp directory if not set.
            StreamingDataset uses either ``streams`` or ``remote``/``local``. Defaults to ``None``.
        split (str, optional): Which dataset split to use, if any. If provided, we stream from/to
            the ``split`` subdirs of  ``remote`` and ``local``. Defaults to ``None``.
        download_retry (int): Number of download re-attempts before giving up. Defaults to ``2``.
        download_timeout (float): Number of seconds to wait for a shard to download before raising
            an exception. Defaults to ``60``.
        validate_hash (str, optional): Optional hash or checksum algorithm to use to validate
            shards. Defaults to ``None``.
        keep_zip (bool): Whether to keep or delete the compressed form when decompressing
            downloaded shards. If ``False``, keep iff remote is local or no remote. Defaults to
            `False``.
        keep_raw (bool): Whether to keep or delete the decompressed form (or only form)
            of shards after all their samples have been yielded this epoch. If ``False``, keep iff
            remote is local or no remote and no compression. Defaults to ``True``.
        choose (int, optional): Number of samples to draw per epoch balanced across all streams.
            If ``None``, takes its value from the total number of underlying samples. Provide this
            field if you are weighting streams relatively to target a larger or smaller epoch size.
            Defaults to ``None``.
        predownload (int, optional): Target number of samples ahead to download the shards of while
            iterating. Defaults to ``100_000``.
        partition_algo (str): Which partitioning algorithm to use. Defaults to ``orig``.
        num_canonical_nodes (int, optional): Canonical number of nodes for shuffling with
            resumption. Defaults to ``None``, which is interpreted as the number of nodes of the
            initial run.
        batch_size (int, optional): Batch size of its DataLoader, which affects how the dataset is
            partitioned over the workers. Defaults to ``None``.
        shuffle (bool): Whether to iterate over the samples in randomized order. Defaults to
            ``False``.
        shuffle_algo (str): Which shuffling algorithm to use. Defaults to ``py1b``.
        shuffle_seed (int): Seed for Deterministic data shuffling. Defaults to ``9176``.
        shuffle_block_size (int): Unit of shuffle. Defaults to ``1 << 18``.
        transforms (callable, optional): A function/transforms that takes in an image and a label
            and returns the transformed versions of both. Defaults to ``None``.
        transform (callable, optional): A function/transform that takes in an image and returns a
            transformed version. Defaults to ``None``.
        target_transform (callable, optional): A function/transform that takes in a target and
            returns a transformed version. Defaults to ``None``.
    """

    def __init__(self,
                 *,
                 remote: Optional[str] = None,
                 local: Optional[str] = None,
                 split: Optional[str] = None,
                 download_retry: int = 2,
                 download_timeout: float = 60,
                 validate_hash: Optional[str] = None,
                 keep_zip: bool = False,
                 keep_raw: bool = True,
                 choose: Optional[int] = None,
                 predownload: Optional[int] = 100_000,
                 partition_algo: str = 'orig',
                 num_canonical_nodes: Optional[int] = None,
                 batch_size: Optional[int] = None,
                 shuffle: bool = False,
                 shuffle_algo: str = 'py1b',
                 shuffle_seed: int = 9176,
                 shuffle_block_size: int = 1 << 18,
                 transforms: Optional[Callable] = None,
                 transform: Optional[Callable] = None,
                 target_transform: Optional[Callable] = None) -> None:
        StreamingDataset.__init__(self,
                                  remote=remote,
                                  local=local,
                                  split=split,
                                  download_retry=download_retry,
                                  download_timeout=download_timeout,
                                  validate_hash=validate_hash,
                                  keep_zip=keep_zip,
                                  keep_raw=keep_raw,
                                  predownload=predownload,
                                  partition_algo=partition_algo,
                                  num_canonical_nodes=num_canonical_nodes,
                                  batch_size=batch_size,
                                  shuffle=shuffle,
                                  shuffle_algo=shuffle_algo,
                                  shuffle_seed=shuffle_seed,
                                  shuffle_block_size=shuffle_block_size)

        has_transforms = transforms is not None
        has_separate_transform = transform is not None or target_transform is not None
        if has_transforms and has_separate_transform:
            raise ValueError(
                'Only transforms or transform/target_transform can be passed as an argument')

        self.transform = transform
        self.target_transform = target_transform
        if not has_transforms:
            transforms = StandardTransform(transform, target_transform)
        self.transforms = transforms

    def get_item(self, idx: int) -> Any:
        """Get sample by global index, blocking to load its shard if missing.

        Args:
            idx (int): Sample index.

        Returns:
            Any: Sample data.
        """
        obj = super().get_item(idx)
        x = obj['x']
        y = obj['y']
        return self.transforms(x, y)
