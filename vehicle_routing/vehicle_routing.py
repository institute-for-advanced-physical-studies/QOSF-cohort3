import numpy as np
import dimod

from qiskit.optimization.converters import InequalityToEquality, IntegerToBinary, LinearEqualityToPenalty
from solver_backend import SolverBackend


class VehicleRouter:

    def __init__(self, n_clients=None, n_vehicles=None, cost_matrix=None, **params):

        # Store critical inputs
        self.n = n_clients
        self.m = n_vehicles
        self.c = np.array(cost_matrix)

        # Extract parameters
        self.penalty = params.setdefault('constraint_penalty', 900)
        self.chain_strength = params.setdefault('chain_strength', 1000)
        self.num_reads = params.setdefault('num_reads', 1000)
        self.solver = params.setdefault('solver', 'dwave')

        # Initialize quadratic structures
        self.qp = None
        self.qubo = None
        self.bqm = None
        self.variables = None

        # Initialize result containers
        self.result = None
        self.solution = None

        # Build quadratic models
        self.rebuild()

    def build_quadratic_program(self):

        # Dummy. Override in child class.
        pass

    def build_qubo(self):

        # Create converters
        converter_a = InequalityToEquality()
        converter_b = IntegerToBinary()
        converter_c = LinearEqualityToPenalty(penalty=self.penalty)

        # Convert to QUBO
        self.qubo = converter_a.convert(self.qp)
        self.qubo = converter_b.convert(self.qubo)
        self.qubo = converter_c.convert(self.qubo)

    def build_bqm(self):

        # Extract qubo data
        Q = self.qubo.objective.quadratic.to_dict(use_name=True)
        g = self.qubo.objective.linear.to_dict(use_name=True)
        c = self.qubo.objective.constant

        # Build BQM
        self.bqm = dimod.BQM(g, Q, c, dimod.BINARY)

    def rebuild(self):

        # Rebuild quadratic models
        self.build_quadratic_program()
        self.build_qubo()
        self.build_bqm()

    def extract_solution(self, result_dict):

        # Extract solution from result dictionary
        var_list = self.variables.reshape(-1)
        self.solution = np.zeros(var_list.shape)
        for i in range(len(var_list)):
            self.solution[i] = result_dict[var_list[i]]

        # Reshape result
        self.solution = self.solution.reshape(self.variables.shape)

    def evaluate_qubo_cost(self, data=None):

        # Resolve data
        if data is None:
            data = self.solution.reshape(-1)
        else:
            data = np.array(data).reshape(-1)

        # Resolve variables
        var_list = self.variables.reshape(-1)
        data_dict = {var_list[i]: data[i] for i in range(len(data))}

        # Extract Q matrix
        Q = self.qubo.objective.quadratic.to_array()
        g = np.array([self.qubo.objective.linear.to_array()])
        c = self.qubo.objective.constant

        # Build input vector
        x = np.zeros((self.qubo.get_num_binary_vars(), 1))
        for var, i in self.qubo.variables_index.items():
            x[i, 0] = data_dict[var]

        # Evaluate output
        cost = np.dot(g, x) + np.dot(np.dot(np.transpose(x), Q), x) + c
        return cost[0][0]

    def solve(self, **params):

        # Resolve solver
        params.setdefault('solver', self.solver)

        # Solve
        backend = SolverBackend(self)
        backend.solve(**params)