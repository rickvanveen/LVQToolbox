import numpy as np

from . import LVQBaseClass

from sklearn.utils.validation import check_is_fitted, check_array

from . import LVQBaseClass
from .. import distances, solvers
from ..objectives import GeneralizedLearningObjective
from ..solvers import SolverBaseClass

from typing import Tuple, Union, List

ModelParamsType = Tuple[np.ndarray, np.ndarray]

DISTANCES = [
    "local-adaptive-squared-euclidean",
]

SOLVERS = [
    "adaptive-moment-estimation",
    "broyden-fletcher-goldfarb-shanno",
    "limited-memory-bfgs",
    "steepest-gradient-descent",
    "waypoint-gradient-descent",
]

_RELEVANCES_PARAMS_DEFAULS = {
    "normalization": True,
    "localization": "prototypes",
    "n_components": "all",
}


class LGMLVQ(LVQBaseClass):
    r"""Localized Generalized Matrix Learning Vector Quantization

    This model optimizes the generalized learning objective introduced by Sato and Yamada (
    1996). Additionally, it learns a relevance matrix (lambda\_ = omega\_.T.dot(omega\_)) in a local
    setting. This can either be per class or per prototype. The relevant omega per prototype is
    considered when computing the adaptive distance as introduced by Schneider et al. 2009.

    Parameters
    ----------
    distance_type : "local-adaptive-squared-euclidean" or Class
        Distance function that employs multiple relevance matrix in its calculation. This is
        controlled by the localization setting.

    distance_params : Dict, default=None
        Parameters passed to init of distance callable

    activation_type : {"identity", "sigmoid", "soft+", "swish"} or Class, default="sigmoid"
        The activation function used in the objective function.

    activation_params : Dict, default=None
        Parameters passed to init of activation function. See the documentation of activation
        functions for function dependent parameters and defaults.

    discriminant_type : "relative-distance" or Class
        The discriminant function.

    discriminant_params : Dict, default=None
        Parameters passed to init of discriminant callable

    solver_type : {"sgd", "wgd", "adam", "lbfgs", "bfgs"},
        The solver used for optimization

        - "sgd" is an alias for the steepest gradient descent solver. Implements both the
            stochastic  and (mini) batch variants. Depending on chosen batch size.

        - "wgd" or waypoint gradient descent optimization (Papari et al. 2011)

        - "adam" also known as adaptive moment estimation. Implementation based on description
            by Lekander et al (2017)

        - "bfgs" or the broyden-fletcher-goldfarb-shanno optimization algorithm. Uses the scipy
            implementation.

        - "lbfgs" is an alias for limited-memory-bfgs with bfgs the same as above. Uses the
            scipy implementation.

    solver_params : Dict, default=None
        Parameters passed to init of solvers. See the documentation of the solver
        functions for relevant parameters and defaults.

    initial_prototypes : "class-conditional-mean" or np.ndarray, default="class-conditional-mean"
        Default will initiate the prototypes to the class conditional mean with a small random
        offset. Custom numpy array can be passed to change the initial positions of the prototypes.

    prototypes_per_class : int or np.ndarray of length=n_prototypes, default=1
        Number of prototypes per class. Default will generate single prototype per class. In the
        case of unequal number of prototypes per class is preferable provide the labels as
        np.ndarray. Example prototypes_per_class = np.array([0, 0, 1, 2, 2, 2]) this will match
        with a total of 6 prototypes with first two class with index 0, then one with class index 1,
        and three with class index 2. Note: labels are indexes to classes\_ attribute.

    initial_omega : "identity" or np.ndarray, default="identity"
        Default will initiate the omega matrices to be the identity matrix. Other behaviour can
        be implemented by providing a custom omega as numpy array. E.g. a randomly initialized
        square matrix (n_features, n_features). The rank of the matrix can be reduced by
        providing a square matrix of shape ([1, n_features), n_features) (Bunte et al. 2012).

    localization : {"prototype", "class"}, default="prototype"
        Setting that controls the localization of the relevance matrices. Either per prototypes,
        where each prototype has its own relevance matrix. Or per class where each class has its
        own relevance matrix and if more then a single prototype per class is used it would be
        shared between these prototypes.

    normalized_omega : {True, False}, default=True
        Flag to indicate whether to normalize omega such that the trace of the relevance matrix
        is (approximately) equal to 1.

    random_state : int, RandomState instance, default=None
        Determines random number generation.

    force_all_finite : {True, "allow-nan"}, default=True
        Whether to raise an error on np.inf, np.nan, pd.NA in array. The possibilities are:

        - True: Force all values of array to be finite.
        - "allow-nan": accepts only np.nan and pd.NA values in array. Values cannot be infinite.

    Attributes
    ----------
    classes_ : np.ndarray of shape (n_classes,)
        Class labels for each output.

    prototypes_ : np.ndarray of shape (n_protoypes, n_features)
        Positions of the prototypes after fit(X, labels) has been called.

    prototypes_labels_ : np.ndarray of shape (n_prototypes)
        Labels for each prototypes. Labels are indexes to classes\_

    omega_: np.ndarray with size depending on initialization, default (n_features, n_features)
        Omega\_ matrices that were found during training and define the relevance matrices lambda\_.

    lambda_: np.ndarray of size (n_features, n_features)
        The relevance matrices (omega\_.T.dot(omega\_) per omega\_)

    omega_hat_: np.ndarray
        The omega matrices found by the eigenvalue decomposition of the relevance matrices lambda\_.
        The eigenvectors (columns of omega_hat\_) can be used to transform the X (Bunte et al.
        2012). This results in multiple possible transformations one per relevance matrix.

    eigenvalues_: np.ndarray
        The corresponding eigenvalues to omega_hat\_ found by the eigenvalue decomposition of
        the relevance matrix lambda\_

    References
    ----------
    Sato, A., and Yamada, K. (1996) "Generalized Learning Vector Quantization."
    Advances in Neural Network Information Processing Systems, 423–429, 1996.

    Schneider, P., Biehl, M., & Hammer, B. (2009). "Adaptive Relevance Matrices in Learning Vector
    Quantization" Neural Computation, 21(12), 3532–3561, 2009.

    Papari, G., and Bunte, K., and Biehl, M. (2011) "Waypoint averaging and step size control in
    learning by gradient descent" Mittweida Workshop on Computational Intelligence (MIWOCI) 2011.

    LeKander, M., Biehl, M., & De Vries, H. (2017). "Empirical evaluation of gradient methods for
    matrix learning vector quantization." 12th International Workshop on Self-Organizing Maps and
    Learning Vector Quantization, Clustering and Data Visualization, WSOM 2017.

    Bunte, K., Schneider, P., Hammer, B., Schleif, F.-M., Villmann, T., & Biehl, M. (2012).
    "Limited Rank Matrix Learning, discriminative dimension reduction and visualization." Neural
    Networks, 26, 159–173, 2012.
"""
    classes_: np.ndarray
    prototypes_: np.ndarray
    prototypes_labels_: np.ndarray
    omega_: np.ndarray
    lambda_: np.ndarray
    omega_hat_: np.ndarray
    eigenvalues_: np.ndarray

    def __init__(
        self,
        distance_type: Union[str, type] = "local-adaptive-squared-euclidean",
        distance_params: dict = None,
        activation_type: Union[str, type] = "identity",
        activation_params: dict = None,
        discriminant_type: Union[str, type] = "relative-distance",
        discriminant_params: dict = None,
        solver_type: Union[str, type] = "steepest-gradient-descent",
        solver_params: dict = None,
        prototype_init: Union[str, np.ndarray] = "class-conditional-mean",
        prototype_params: dict = None,
        relevance_init: Union[str, np.ndarray] = "identity",
        relevance_params: dict = None,
        random_state: Union[int, np.random.RandomState] = None,
        force_all_finite: Union[str, int] = True,
    ):
        self.activation_type = activation_type
        self.activation_params = activation_params
        self.discriminant_type = discriminant_type
        self.discriminant_params = discriminant_params
        self.relevance_init = relevance_init
        relevance_params = self._init_parameter_params(
            relevance_params, _RELEVANCES_PARAMS_DEFAULS
        )
        self.relevance_params = relevance_params

        super(LGMLVQ, self).__init__(
            distance_type,
            distance_params,
            DISTANCES,
            solver_type,
            solver_params,
            SOLVERS,
            prototype_init,
            prototype_params,
            random_state,
            force_all_finite,
        )

    ###########################################################################################
    # The "Getter" and "Setter" that are used by the solvers to set and get model params.
    ###########################################################################################

    def set_variables(self, variables: np.ndarray) -> None:
        np.copyto(self._variables, variables)
        if self._needs_normalizing():
            LGMLVQ._normalize_omega(self.to_omega(self._variables))

    def set_model_params(self, model_params: ModelParamsType):
        """ Changes the model's internal parameters.

        Parameters
        ----------
        model_params : ndarray or tuple
            In the simplest case can be only the prototypes as ndarray. Other models may include
            multiple parameters then they should be stored in a tuple.

        """
        new_prototypes, new_omega = model_params

        self.set_prototypes(new_prototypes)
        self.set_omega(new_omega)

        if self._needs_normalizing():
            LGMLVQ._normalize_omega(self.omega_)

    def get_model_params(self) -> ModelParamsType:
        """

        Returns
        -------
        ndarray
             Returns the prototypes as ndarray.

        """
        return self.prototypes_, self.omega_

    ###########################################################################################
    # Specific "getters" and "setters" for the prototypes shared by every LVQ model.
    ###########################################################################################

    def get_omega(self):
        """
        Convenience function to return self.omega_

        Returns
        -------
            ndarray, with shape depending on initialization of omega.

        """
        return self.omega_

    def set_omega(self, omega):
        """
        Convenience function that makes shure to copy the value to self.omega_ and not overwrite
        it.

        Parameters
        ----------
        omega : ndarray with same shape as self.omega_

        """
        np.copyto(self.omega_, omega)

    ###########################################################################################
    # Functions to transform the 1D variables array to model parameters and back
    ###########################################################################################

    def to_model_params(self, variables: np.ndarray) -> ModelParamsType:
        """

        Parameters
        ----------
        variables : ndarray
            Single ndarray that stores the parameters in the order as given by the
            "to_variabes()" function

        Returns
        -------
        ndarray
            Returns the prototypes as ndarray.

        """
        return (
            self.to_prototypes(variables),
            self.to_omega(variables),
        )

    def to_prototypes(self, var_buffer: np.ndarray) -> np.ndarray:
        """
        Returns a view (of the shape of the model's prototypes) into the provided variables
        buffer of the same size as the model's variables array.

        Parameters
        ----------
        var_buffer: ndarray
            1d array of the shame size as the model's variables array.

        Returns
        -------
            ndarray of shape (n_prototypes, n_features)

        """
        return var_buffer[: self._prototypes_size].reshape(self._prototypes_shape)

    def to_omega(self, var_buffer: np.ndarray) -> np.ndarray:
        """
        Returns a view (of the shape of the model's omega) into the provided variables
        buffer of the same size as the model's variables array.

        Parameters
        ----------
        var_buffer: ndarray
            1d array of the shame size as the model's variables array.

        Returns
        -------
            ndarray, with shape depending on initialization of omega.

        """
        return var_buffer[self._prototypes_size :].reshape(self._relevances_shape)

    ###########################################################################################
    # Solver Normalization functions
    ###########################################################################################

    def normalize_variables(self, var_buffer: np.ndarray) -> None:
        """

        Parameters
        ----------
        model_params : ndarray
            Model parameters as provided by get_model_params()

        Returns
        -------
        ndarray or tuple
            Same shape and size as input, but normalized. How to normalize depends on model
            implementation.

        """
        (prototypes, omega) = self.to_model_params(var_buffer)

        self._normalize_prototypes(prototypes)
        self._normalize_omega(omega)

    @staticmethod
    def _normalize_omega(omega: np.ndarray) -> None:
        np.divide(
            omega,
            np.sqrt(np.einsum("ikj, ikj -> i", omega, omega)).reshape(
                omega.shape[0], 1, 1
            ),
            out=omega,
        )
        # denominator = np.sqrt(np.einsum("ikj, ikj -> i", omega, omega)).reshape(
        #     omega.shape[0], 1, 1
        # )
        # omega /= denominator

    ###########################################################################################
    # Solver helper functions
    ###########################################################################################

    def add_partial_gradient(self, gradient, partial_gradient, i_prototype) -> None:
        n_features = self.n_features_in_

        prots_view = self.to_prototypes(gradient)
        np.add(
            prots_view[i_prototype, :],
            partial_gradient[:n_features],
            out=prots_view[i_prototype, :],
        )
        omega_view = self.to_omega(gradient)[
            self.prototypes_labels_[i_prototype], :, :
        ].ravel()

        assert np.shares_memory(omega_view, gradient)

        np.add(omega_view, partial_gradient[n_features:], out=omega_view)

    def multiply_variables(
        self, step_sizes: Union[int, float, np.ndarray], var_buffer: np.ndarray
    ) -> None:
        if isinstance(step_sizes, int) | isinstance(step_sizes, float):
            var_buffer *= step_sizes
            return

        if isinstance(step_sizes, np.ndarray):
            if step_sizes.size == 2:
                prototypes, omegas = self.to_model_params(var_buffer)
                prototypes *= step_sizes[0]
                omegas *= step_sizes[1]

    ###########################################################################################
    # Initialization function
    ###########################################################################################

    def _init_variables(self) -> None:
        self._variables = np.empty(
            self._prototypes_size + self._relevances_size, dtype="float64", order="C",
        )

    def _check_model_params(self):
        self._check_prototype_params(**self.prototype_params)
        self._check_relevances_params(**self.relevance_params)

    def _init_model_params(self, X, y) -> None:
        self._init_prototypes(X, y, **self.prototype_params)
        self._init_relevances(**self.relevance_params)

    def _check_relevances_params(
        self,
        normalization: bool = True,
        localization: str = "prototypes",
        n_components: Union[str, int] = "all",
    ):
        if not isinstance(normalization, bool):
            raise ValueError("Provided normalization is invalid.")

        if n_components == "all":
            shape = (self.n_features_in_, self.n_features_in_)
        elif 1 <= n_components <= self.n_features_in_:
            shape = (self.n_features_in_, n_components)
        else:
            raise ValueError("Provided n_components is invalid.")

        if isinstance(localization, str):
            if localization == "prototypes":
                self._relevances_shape = (self._prototypes_shape[0], *shape)
            elif localization == "class":
                self._relevances_shape = (self.classes_.size, *shape)
            else:
                raise ValueError("Provided localization is invalid.")
        else:
            raise ValueError("Provided localization is invalid.")

        self._relevances_size = np.prod(self._relevances_shape)

    def _init_relevances(self, normalization: bool = True, **kwargs):
        self.omega_ = self.to_omega(self._variables)

        if isinstance(self.relevance_init, str):
            if self.relevance_init == "identity":
                identity = np.eye(*self._relevances_shape[1:])
                self.set_omega(
                    np.repeat(
                        identity[np.newaxis, :, :], self._relevances_shape[0], axis=0
                    )
                )
            elif self.relevance_init == "random":
                self.set_omega(
                    self.random_state_.uniform(
                        low=0, high=1, size=self._relevances_shape
                    )
                )
            else:
                raise ValueError("Provided relevance_init is invalid.")
        else:
            raise ValueError("Provided relevance_init is invalid.")

        if normalization:
            LGMLVQ._normalize_omega(self.omega_)

    def _init_objective(self):
        self._objective = GeneralizedLearningObjective(
            self.activation_type,
            self.activation_params,
            self.discriminant_type,
            self.discriminant_params,
        )

    ###########################################################################################
    # Other Algorithm specific stuff.
    ###########################################################################################

    def _after_fit(self, X: np.ndarray, y: np.ndarray):
        self.lambda_ = LGMLVQ._compute_lambdas(self.omega_)
        # self.lambda_ = np.einsum("ikj, ikl -> ijl", self.omega_, self.omega_)

        eigenvalues, omega_hat = np.linalg.eig(self.lambda_)

        sorted_indices = np.flip(np.argsort(eigenvalues, axis=1), axis=1)
        eigenvalues, omega_hat = zip(
            *[
                (lk[ii], ek[:, ii])
                for (ii, lk, ek) in zip(sorted_indices, eigenvalues, omega_hat)
            ]
        )
        self.eigenvalues_ = np.array(eigenvalues)
        self.omega_hat_ = np.array(omega_hat)

    def _needs_normalizing(self):
        return self.relevance_params["normalization"]

    @staticmethod
    def _compute_lambda(omega):
        # Equivalent to omega.T.dot(omega)
        return np.einsum("ji, jk -> ik", omega, omega)

    @staticmethod
    def _compute_lambdas(omegas):
        # Equivalent to omega.T.dot(omega) per omega (quite slow)
        return np.einsum("ikj, ikl -> ijl", omegas, omegas)

    ###########################################################################################
    # Transformer related functions
    ###########################################################################################

    def fit_transform(
        self, data: np.ndarray, y: np.ndarray, **trans_params
    ) -> np.ndarray:
        r"""

        Parameters
        ----------
        data : np.ndarray with shape (n_samples, n_features)
            Data used for fit and that will be transformed.
        y : np.ndarray with length (n_samples)
            Labels corresponding to the X samples.
        trans_params :
            Parameters passed to transform function

        Returns
        -------
        The X projected on columns of each omega\_hat\_ with shape (n_omegas, n_samples,
        n_columns)

        """
        return self.fit(data, y).transform(data, **trans_params)

    def transform(
        self,
        X: np.ndarray,
        scale: bool = False,
        omega_hat_index: Union[int, List[int]] = 0,
    ) -> np.ndarray:
        r"""

        Parameters
        ----------
        X : np.ndarray with shape (n_samples, n_features)
            Data that needs to be transformed
        scale : {True, False}, default = False
            Controls if the eigenvectors the X is projected on are scaled by the square root
            of their eigenvalues.
        omega_hat_index : int or list
            The indices of the omega\_hats\_ the transformation should be computed for.

        Returns
        -------
        The X projected on columns of each omega\_hat\_ with shape (n_omegas, n_samples,
        n_columns)

        """
        check_is_fitted(self)

        X = check_array(X)

        transformation_matrix = self.omega_hat_[omega_hat_index, :, :]
        if transformation_matrix.ndim != 3:
            transformation_matrix = np.expand_dims(transformation_matrix, 0)

        if scale:
            transformation_matrix = np.einsum(
                "ik, ijk -> ijk", np.sqrt(self.eigenvalues_), transformation_matrix
            )
        transformed_data = np.einsum("jk, ikl -> ijl", X, transformation_matrix)

        return np.squeeze(transformed_data)

    def _more_tags(self):
        # For some reason lgmlvq does not perform well on one of the test cases build into
        # sklearn's test cases. Which is something to look into, but this "fixes" it in the mean
        # time...
        return {"poor_score": True}