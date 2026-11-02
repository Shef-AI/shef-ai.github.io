

set -ex



pip check
python -m conda create --dry-run python --solver=rattler
pytest -vv tests  --deselect=tests/test_channels.py::test_conda_build_with_aliased_channels --deselect=tests/test_downstream.py::test_build_recipe --deselect=tests/test_downstream.py::test_conda_lock --deselect=tests/test_performance.py::test_install_vaex_from_conda_forge_and_defaults --deselect=tests/test_solver_differences.py::test_gpu_cpu_mutexes --deselect=tests/test_solver_differences.py::test_old_panel --deselect=tests/test_solver.py::TestRattlerSolver::test_empty --deselect=tests/test_solver.py::TestRattlerSolver::test_anaconda_nomkl --deselect=tests/test_solver.py::TestRattlerSolver::test_unsat_from_r1 --deselect=tests/test_solver.py::TestRattlerSolver::test_get_dists --deselect=tests/test_solver.py::TestRattlerSolver::test_timestamps_and_deps --deselect=tests/test_solver.py::TestRattlerSolver::test_nonexistent_deps --deselect=tests/test_solver.py::TestRattlerSolver::test_install_package_with_feature --deselect=tests/test_solver.py::TestRattlerSolver::test_circular_dependencies --deselect=tests/test_solver.py::TestRattlerSolver::test_irrational_version --deselect=tests/test_solver.py::test_too_aggressive_update_to_conda_forge_packages --deselect=tests/test_solver.py::test_pinned_with_cli_build_string  --deselect=tests/test_solve_comparison_benchmarks.py::test_solve_update_all_large_lockfile
exit 0
