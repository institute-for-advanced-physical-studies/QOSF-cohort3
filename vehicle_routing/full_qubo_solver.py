import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from collections import Counter
from matplotlib.colors import rgb2hex
from vehicle_routing import VehicleRouter
from qiskit.optimization import QuadraticProgram


class FullQuboSolver(VehicleRouter):

    def __init__(self, n_clients=None, n_vehicles=None, cost_matrix=None, **params):

        # Call parent initializer
        super().__init__(n_clients, n_vehicles, cost_matrix, **params)

    def build_quadratic_program(self):

        # Initialization
        self.qp = QuadraticProgram(name='Vehicle Routing Problem')

        # Designate variable names
        self.variables = np.array([[['x.{}.{}.{}'.format(i, j, k) for k in range(1, self.n + 1)]
                                    for j in range(self.n + 1)] for i in range(1, self.m + 1)])

        # Add variables to quadratic program
        for var in self.variables.reshape(-1):
            self.qp.binary_var(name=var)

        # Build objective function
        obj_linear_a = {self.variables[m, n, 0]: self.c[0, n] for m in range(self.m) for n in range(1, self.n + 1)}
        obj_linear_b = {self.variables[m, n, -1]: self.c[n, 0] for m in range(self.m) for n in range(1, self.n + 1)}
        obj_quadratic = {(self.variables[m, i, n], self.variables[m, j, n + 1]): self.c[i, j] for m in range(self.m)
                         for n in range(self.n - 1) for i in range(self.n + 1) for j in range(self.n + 1)}

        # Add objective to quadratic program
        self.qp.minimize(linear=dict(Counter(obj_linear_a) + Counter(obj_linear_b)), quadratic=obj_quadratic)

        # Add constraints - single delivery per client
        for k in range(1, self.n + 1):
            constraint_linear = {self.variables[i, k, j]: 1 for i in range(self.m) for j in range(self.n)}
            self.qp.linear_constraint(linear=constraint_linear, sense='==', rhs=1, name=f'single_delivery_{k}')

        # Add constraints - vehicle at one place at one time
        for m in range(self.m):
            for n in range(self.n):
                constraint_linear = {self.variables[m, k, n]: 1 for k in range(self.n + 1)}
                self.qp.linear_constraint(linear=constraint_linear, sense='==', rhs=1,
                                          name=f'single_location_{m + 1}_{n + 1}')

    def visualize(self, xc=None, yc=None):

        # Resolve coordinates
        if xc is None:
            xc = (np.random.rand(self.n + 1) - 0.5) * 10
        if yc is None:
            yc = (np.random.rand(self.n + 1) - 0.5) * 10

        # Initialize figure
        plt.figure()
        ax = plt.gca()
        ax.set_title(f'Vehicle Routing Problem - {self.n} Clients & {self.m} Cars')
        cmap = plt.cm.get_cmap('Accent')

        # Build graph
        G = nx.MultiDiGraph()
        G.add_nodes_from(range(self.n + 1))

        # Plot nodes
        pos = {i: (xc[i], yc[i]) for i in range(self.n + 1)}
        labels = {i: str(i) for i in range(self.n + 1)}
        nx.draw_networkx_nodes(G, pos=pos, ax=ax, node_color='b', node_size=500, alpha=0.8)
        nx.draw_networkx_labels(G, pos=pos, labels=labels, font_size=16)

        # Loop over cars
        for i in range(self.solution.shape[0]):

            # Get route
            var_list = np.transpose(self.variables[i]).reshape(-1)
            sol_list = np.transpose(self.solution[i]).reshape(-1)
            active_vars = [var_list[k] for k in range(len(var_list)) if sol_list[k] == 1]
            route = [int(var.split('.')[2]) for var in active_vars]

            # Plot edges
            edgelist = [(0, route[0])] + [(route[j], route[j + 1]) for j in range(len(route) - 1)] + [(route[-1], 0)]
            G.add_edges_from(edgelist)
            nx.draw_networkx_edges(G, pos=pos, edgelist=edgelist, width=2, edge_color=rgb2hex(cmap(i)))

        # Show plot
        plt.grid(True)
        plt.show()