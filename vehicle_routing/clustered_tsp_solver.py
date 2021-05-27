import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

from itertools import product
from collections import Counter
from matplotlib.colors import rgb2hex
from vehicle_routing import VehicleRouter
from node_clustering import NodeClustering
from qiskit_optimization import QuadraticProgram


class ClusteredTspSolver(VehicleRouter):

    def __init__(self, n_clients, n_vehicles, cost_matrix, **params):

        # Initialize cluster data
        self.cluster = None
        self.cluster_dict = None

        # Call parent initializer
        super().__init__(n_clients, n_vehicles, cost_matrix, **params)

    def build_quadratic_program(self):

        # Initialization
        self.qp = QuadraticProgram(name='Vehicle Routing Problem')

        # Cluster nodes
        self.cluster = NodeClustering(self.n, self.m, self.c[1:, 1:])
        self.cluster.solve()
        self.cluster_dict = {i: [j + 1 for j in range(self.n) if self.cluster.solution[j] == i] for i in range(self.m)}

        # Designate variable names
        self.variables = []
        for i in range(self.m):
            node_list = self.cluster_dict[i]
            self.variables += [f'x.{i}.{j}.{k}' for k in range(1, len(node_list) + 1) for j in node_list]
        self.variables = np.array(self.variables)

        # Add variables to quadratic program
        for var in self.variables:
            self.qp.binary_var(name=var)

        # Initialize objective function containers
        obj_linear_a = {}
        obj_linear_b = {}
        obj_quadratic = {}

        # Build objective function
        for i in range(self.m):

            # Extract cluster
            node_list = self.cluster_dict[i]
            edgelist = [(j, k) for j, k in product(node_list, repeat=2) if j != k]

            # Build quadratic terms
            for j, k in edgelist:
                for t in range(1, len(node_list)):
                    obj_quadratic[(f'x.{i}.{j}.{t}', f'x.{i}.{k}.{t + 1}')] = self.c[j, k]

            # Build linear terms
            for j in node_list:
                obj_linear_a[f'x.{i}.{j}.{1}'] = self.c[0, j]
                obj_linear_b[f'x.{i}.{j}.{len(node_list)}'] = self.c[j, 0]

        # Add objective to quadratic program
        self.qp.minimize(linear=dict(Counter(obj_linear_a) + Counter(obj_linear_b)), quadratic=obj_quadratic)

        # Add constraints - single delivery per client
        for i in range(self.m):
            node_list = self.cluster_dict[i]
            for j in node_list:
                constraint_linear = {f'x.{i}.{j}.{k}': 1 for k in range(1, len(node_list) + 1)}
                self.qp.linear_constraint(linear=constraint_linear, sense='==', rhs=1, name=f'single_delivery_{i}_{j}')

        # Add constraints - vehicle at one place at one time
        for i in range(self.m):
            node_list = self.cluster_dict[i]
            for k in range(1, len(node_list) + 1):
                constraint_linear = {f'x.{i}.{j}.{k}': 1 for j in node_list}
                self.qp.linear_constraint(linear=constraint_linear, sense='==', rhs=1, name=f'single_location_{i}_{k}')

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
        node_colors = [rgb2hex(cmap(self.m))] + [rgb2hex(cmap(i)) for i in self.cluster.solution]

        # Plot nodes
        pos = {i: (xc[i], yc[i]) for i in range(self.n + 1)}
        labels = {i: str(i) for i in range(self.n + 1)}
        nx.draw_networkx_nodes(G, pos=pos, ax=ax, node_color=node_colors, node_size=500, alpha=0.8)
        nx.draw_networkx_labels(G, pos=pos, labels=labels, font_size=16)

        # Evaluate active variables
        active_vars = [self.variables[k] for k in range(len(self.variables)) if self.solution[k] == 1]

        # Loop over cars
        for i in range(self.m):

            # Get route
            route = [int(var.split('.')[2]) for var in active_vars if int(var.split('.')[1]) == i]

            # Plot edges
            edgelist = [(0, route[0])] + [(route[j], route[j + 1]) for j in range(len(route) - 1)] + [(route[-1], 0)]
            G.add_edges_from(edgelist)
            nx.draw_networkx_edges(G, pos=pos, edgelist=edgelist, width=2, edge_color=rgb2hex(cmap(i)))

        # Show plot
        plt.grid(True)
        plt.show()