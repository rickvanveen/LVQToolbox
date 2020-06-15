from .base import DistanceBaseClass

from sklvq.distances.euclidean import Euclidean
from sklvq.distances.nan_euclidean import NanEuclidean
from sklvq.distances.squared_euclidean import SquaredEuclidean
from sklvq.distances.squared_nan_euclidean import SquaredNanEuclidean
from sklvq.distances.adaptive_squared_euclidean import AdaptiveSquaredEuclidean
from sklvq.distances.adaptive_squared_nan_euclidean import AdaptiveSquaredNanEuclidean
from sklvq.distances.local_adaptive_squared_euclidean import (
    LocalAdaptiveSquaredEuclidean,
)
from sklvq.distances.local_adaptive_squared_nan_euclidean import (
    LocalAdaptiveSquaredNanEuclidean,
)

from typing import Union
from typing import List

from sklvq.misc import utils

__all__ = [
    "DistanceBaseClass",
    "Euclidean",
    "NanEuclidean",
    "SquaredEuclidean",
    "SquaredNanEuclidean",
    "AdaptiveSquaredEuclidean",
    "AdaptiveSquaredNanEuclidean",
    "LocalAdaptiveSquaredEuclidean",
    "LocalAdaptiveSquaredNanEuclidean",
]

ALIASES = {"sqeuclidean": "squared-euclidean"}
PACKAGE = "sklvq.distances"


def grab(
    class_type: Union[str, type],
    class_args: list = None,
    class_kwargs: dict = None,
    whitelist: list = None,
) -> Union[DistanceBaseClass, object]:

    return utils.grab(
        class_type, class_args, class_kwargs, ALIASES, whitelist, PACKAGE
    )
