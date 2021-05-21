import hybrid
import dwave.inspector

from dwave.system import DWaveSampler, EmbeddingComposite
from qiskit.optimization.algorithms import MinimumEigenOptimizer
from qiskit.aqua.algorithms import QAOA
from qiskit import Aer


class SolverBackend:

    def __init__(self, vrp):

        # Store relevant data
        self.vrp = vrp
        self.solvers = {'dwave': self.solve_dwave,
                        'hybrid': self.solve_hybrid,
                        'qaoa': self.solve_qaoa}

    def solve(self, solver, **params):

        # Select solver and solve
        solver = self.solvers[solver]
        solver(**params)

    def solve_dwave(self, **params):

        # Resolve parameters
        params['solver'] = 'dwave'
        inspect = params.setdefault('inspect', False)

        # Solve
        sampler = EmbeddingComposite(DWaveSampler())
        self.vrp.result = sampler.sample(self.vrp.bqm, num_reads=self.vrp.num_reads,
                                         chain_strength=self.vrp.chain_strength)

        # Extract solution
        result_dict = self.vrp.result.first.sample
        self.vrp.extract_solution(result_dict)

        # Inspection
        if inspect:
            dwave.inspector.show(self.vrp.result)

    def solve_hybrid(self, **params):

        # Resolve parameters
        params['solver'] = 'hybrid'

        # Build sampler workflow
        workflow = hybrid.Loop(
            hybrid.RacingBranches(
                hybrid.InterruptableTabuSampler(),
                hybrid.EnergyImpactDecomposer(size=30, rolling=True, rolling_history=0.75)
                | hybrid.QPUSubproblemAutoEmbeddingSampler()
                | hybrid.SplatComposer()) | hybrid.ArgMin(), convergence=3)

        # Solve
        sampler = hybrid.HybridSampler(workflow)
        self.vrp.result = sampler.sample(self.vrp.bqm, num_reads=self.vrp.num_reads,
                                         chain_strength=self.vrp.chain_strength)

        # Extract solution
        result_dict = self.vrp.result.first.sample
        self.vrp.extract_solution(result_dict)

    def solve_qaoa(self, **params):

        # Resolve parameters
        params['solver'] = 'qaoa'

        # Build optimizer and solve
        solver = QAOA(quantum_instance=Aer.get_backend('qasm_simulator'))
        optimizer = MinimumEigenOptimizer(min_eigen_solver=solver)
        self.vrp.result = optimizer.solve(self.vrp.qp)

        # Build result dictionary
        result_dict = {self.vrp.result.variable_names[i]: self.vrp.result.x[i]
                       for i in range(len(self.vrp.result.variable_names))}

        # Extract solution
        self.vrp.extract_solution(result_dict)