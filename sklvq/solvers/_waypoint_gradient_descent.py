import numpy as np
from sklearn.utils import shuffle

from . import SolverBaseClass
from ..objectives import ObjectiveBaseClass
from ._base import _update_state

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sklvq.models import LVQBaseClass

STATE_KEYS = ["variables", "nit", "fun", "nfun", "tfun", "step_size"]


class WaypointGradientDescent(SolverBaseClass):
    """ Waypoint gradient descent (WGD)

    Implements the waypoint average optimization scheme. Original description in [1]_.
    Implementation based on description given in [2]_.

    Parameters
    ----------
    objective: ObjectiveBaseClass, required
       This is set by the algorithm. See :class:`sklvq.models.GLVQ`, :class:`sklvq.models.GMLVQ`,
        and :class:`sklvq.models.LGMLVQ`.

    max_runs: int
        Maximum number of runs/epochs that will be computed. Should be >= k. Early stopping can
        be implemented by providing a callback function that returns True when the solver should
        stop. See callback documentation below.

    step_size: float or ndarray
        The step size to control the learning rate of the model parameters. If the same step_size
        should be used for all parameters (e.g., prototypes and omega) then a single float is
        sufficient. If separate initial step_sizes should be used per model parameter then this
        should be specified by using a ndarray.

        Whenever the averge update is accepted (has a lower cost) the step sizes are mutliplied
        with the loss factor. When the "regular" update is accepted then the step size(s) are
        multiplied by the gain factor.

    loss: float
        Should be a value less than 1 and controls the learning rate change factor when an
        average waypoint step is accepted.
    gain: float
        Should be a value greater than 1 and controls the learning rate change factor when a
        regular update step is accepted.
    k: int
        The number of runs used to compute the average waypoint over.

    callback: callable
        Callable with signature callable(state). If the callable returns True the solver
        will stop even if max_runs is not reached yet. The state object contains the following:

        - "variables"
            Concatenated 1D ndarray of the model's parameters
        - "nit"
            The current iteration counter.
        - "fun"
            The accepted cost.
        - "nfun"
            The cost of the regular update step.
        - "tfun"
            The cost of the "tentative" update, i.e., the average of the past k updates.
        - "step_size"
            The current step_size(s)


    References
    ----------
    .. [1] Papari, G., and Bunte, K., and Biehl, M. (2011) "Waypoint averaging and step size
        control in learning by gradient descent" Mittweida Workshop on Computational
        Intelligence (MIWOCI) 2011.
    .. [2] LeKander, M., Biehl, M., & De Vries, H. (2017). "Empirical evaluation of gradient
        methods for matrix learning vector quantization." 12th International Workshop on
        Self-Organizing Maps and Learning Vector Quantization, Clustering and Data
        Visualization, WSOM 2017.

    """

    def __init__(
        self,
        objective: ObjectiveBaseClass,
        max_runs: int = 10,
        step_size: float = 0.1,
        loss: float = 2 / 3,
        gain: float = 1.1,
        k: int = 3,
        callback: callable = None,
    ):
        super().__init__(objective)
        if max_runs <= k or max_runs <= 0:
            raise ValueError(
                "{}:  Expected 0 < max_runs > k, but got max_runs = {}".format(
                    type(self).__name__, max_runs
                )
            )
        self.max_runs = max_runs

        if step_size <= 0:
            raise ValueError(
                "{}:  Expected step_size to be > 0, but got step_size = {}".format(
                    type(self).__name__, step_size
                )
            )
        self.step_size = step_size

        if loss <= 0 or loss > 1:
            raise ValueError(
                "{}: Expected loss to be > 0 and < 1, but got loss = {}".format(
                    type(self).__name__, loss
                )
            )
        self.loss = loss

        if gain < 1:
            raise ValueError(
                "{}: Expected gain to be >= 1, but got gain = {}".format(
                    type(self).__name__, gain
                )
            )
        self.gain = gain

        if k <= 1:
            raise ValueError(
                "{}: Expected k to be >= 2, but got k = {}".format(
                    type(self).__name__, k
                )
            )
        self.k = k

        if not callable(callback):
            raise ValueError(
                "{}:  callback is not callable.".format(type(self).__name__)
            )
        self.callback = callback

    def solve(
        self, data: np.ndarray, labels: np.ndarray, model: "LVQBaseClass",
    ):
        """ Solve

        Performs the actual steps of the waypoint gradient descent optimization.

        Parameters
        ----------
        data : ndarray of shape (number of observations, number of dimensions)
            The data.
        labels : ndarray of size (number of observations)
            The labels of the samples in the data.
        model : LVQBaseClass
            The initial model that will also hold the final result
        """

        previous_waypoints = np.empty((self.k, model.get_variables().size))
        tentative_model_variables = np.empty(model.get_variables().size)

        step_size = self.step_size

        if self.callback is not None:
            variables = model.get_variables()
            cost = self.objective(model, data, labels)
            state = _update_state(
                STATE_KEYS, variables=variables, nit="Initial", nfun=cost, fun=cost
            )
            if self.callback(state):
                return

        # Initial runs to get enough gradients to average.
        for i_run in range(0, self.k):
            shuffled_indices = shuffle(
                range(0, labels.size), random_state=model.random_state_
            )

            shuffled_data = data[shuffled_indices, :]
            shuffled_labels = labels[shuffled_indices]

            objective_gradient = self.objective.gradient(
                model, shuffled_data, shuffled_labels
            )

            # Normalize the gradient by gradient/norm(gradient)
            model.normalize_variables(objective_gradient)

            # Multiply params by step_size
            model.mul_step_size(step_size, objective_gradient)

            model.set_variables(
                np.subtract(  # returns out=objective_gradient
                    model.get_variables(), objective_gradient, out=objective_gradient,
                )
            )

            previous_waypoints[np.mod(i_run, self.k), :] = model.get_variables()

            if self.callback is not None:
                cost = self.objective(model, data, labels)
                state = _update_state(
                    STATE_KEYS,
                    variables=model.get_variables(),
                    nit=i_run + 1,
                    nfun=cost,
                    fun=cost,
                    step_size=step_size,
                )
                if self.callback(state):
                    return

        # The remainder of the runs
        for i_run in range(self.k, self.max_runs):
            shuffled_indices = shuffle(
                range(0, labels.size), random_state=model.random_state_
            )

            shuffled_data = data[shuffled_indices, :]
            shuffled_labels = labels[shuffled_indices]

            objective_gradient = self.objective.gradient(
                model, shuffled_data, shuffled_labels
            )

            # Normalize the gradient by gradient/norm(gradient)
            model.normalize_variables(objective_gradient)

            # Multiply params by step_size
            model.mul_step_size(step_size, objective_gradient)

            new_model_variables = np.subtract(  # returns out=objective_gradient
                model.get_variables(), objective_gradient, out=objective_gradient,
            )

            # Tentative average update
            np.mean(previous_waypoints, axis=0, out=tentative_model_variables)

            # Update model
            model.set_variables(tentative_model_variables)

            # Compute cost of tentative update step
            tentative_cost = self.objective(model, shuffled_data, shuffled_labels)

            # Update model
            model.set_variables(new_model_variables)

            # Compute cost of regular update step
            new_cost = self.objective(model, shuffled_data, shuffled_labels)

            if tentative_cost < new_cost:
                model.set_variables(tentative_model_variables)
                step_size = self.loss * step_size
                accepted_cost = tentative_cost
            else:
                step_size = self.gain * step_size
                accepted_cost = new_cost

            # Administration. Store the models parameters.
            previous_waypoints[np.mod(i_run, self.k), :] = model.get_variables()

            if self.callback is not None:
                state = _update_state(
                    STATE_KEYS,
                    variables=model.get_variables(),
                    nit=i_run + 1,
                    tfun=tentative_cost,
                    nfun=new_cost,
                    fun=accepted_cost,
                    step_size=step_size,
                )
                if self.callback(state):
                    return
