# Tests

Small automated tests for the code in `src` go here. Name each file `test_<what>.py`.

`test_xlsx.py` checks our Excel reader, `src/xlsx.py`. The PSGC and Table C loads use it. It checks how we read text, empty cells, numbers and saved formula results. It also checks that cells keep their exact text, and that every row of a sheet is counted once.

Run the tests from the repo root:

```bash
python -m pip install pytest
python -m pytest -q
```

Every pull request runs them too, in the Python check.

Tests are not data checks. A test checks that our code works. The bronze checks in `04_validation` check that the real data is complete and makes sense, and they save their results in `04-validation.dq_results`.
