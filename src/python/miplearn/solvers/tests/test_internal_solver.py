#  MIPLearn: Extensible Framework for Learning-Enhanced Mixed-Integer Optimization
#  Copyright (C) 2020, UChicago Argonne, LLC. All rights reserved.
#  Released under the modified BSD license. See COPYING.md for more details.
from io import StringIO

import pyomo.environ as pe
from miplearn.solvers import RedirectOutput
from miplearn.solvers.cplex import CPLEXSolver
from miplearn.solvers.gurobi import GurobiSolver

from . import _get_instance
from ...problems.knapsack import ChallengeA


def test_redirect_output():
    import sys
    original_stdout = sys.stdout
    io = StringIO()
    with RedirectOutput([io]):
        print("Hello world")
    assert sys.stdout == original_stdout
    assert io.getvalue() == "Hello world\n"


def test_internal_solver_warm_starts():
    for solver in [GurobiSolver(), CPLEXSolver()]:
        instance = _get_instance()
        model = instance.to_model()

        solver.set_instance(instance, model)
        solver.set_warm_start({
            "x": {
                0: 1.0,
                1: 0.0,
                2: 0.0,
                3: 1.0,
            }
        })
        stats = solver.solve(tee=True)
        assert stats["Warm start value"] == 725.0

        solver.set_warm_start({
            "x": {
                0: 1.0,
                1: 1.0,
                2: 1.0,
                3: 1.0,
            }
        })
        stats = solver.solve(tee=True)
        assert stats["Warm start value"] is None

        solver.fix({
            "x": {
                0: 1.0,
                1: 0.0,
                2: 0.0,
                3: 1.0,
            }
        })
        stats = solver.solve(tee=True)
        assert stats["Lower bound"] == 725.0
        assert stats["Upper bound"] == 725.0


def test_internal_solver():
    for solver in [GurobiSolver(), CPLEXSolver()]:
        instance = _get_instance()
        model = instance.to_model()

        solver.set_instance(instance, model)
        stats = solver.solve(tee=True)
        assert len(stats["Log"]) > 100
        assert stats["Lower bound"] == 1183.0
        assert stats["Upper bound"] == 1183.0
        assert stats["Sense"] == "max"
        assert isinstance(stats["Wallclock time"], float)
        assert isinstance(stats["Nodes"], int)

        solution = solver.get_solution()
        assert solution["x"][0] == 1.0
        assert solution["x"][1] == 0.0
        assert solution["x"][2] == 1.0
        assert solution["x"][3] == 1.0

        stats = solver.solve_lp()
        assert round(stats["Optimal value"], 3) == 1287.923

        solution = solver.get_solution()
        assert round(solution["x"][0], 3) == 1.000
        assert round(solution["x"][1], 3) == 0.923
        assert round(solution["x"][2], 3) == 1.000
        assert round(solution["x"][3], 3) == 0.000

        model.cut = pe.Constraint(expr=model.x[0] <= 0.5)
        solver.add_constraint(model.cut)
        solver.solve_lp()
        assert model.x[0].value == 0.5


def test_node_count():
    for solver in [GurobiSolver(),
                   GurobiSolver(use_lazy_callbacks=False),
                   CPLEXSolver()]:
        challenge = ChallengeA()
        solver.set_time_limit(1)
        solver.set_instance(challenge.test_instances[0])
        stats = solver.solve(tee=True)
        assert stats["Nodes"] > 1