# backend

Python package host for the Studio API (`portfolio_api`). The baseline (U0, S0) ships an
almost empty package so CI can build a wheel and run the fake-identity-provider guard over a
real build output. The owning units (U3 and later) add the API itself.

Build the wheel:

```
python -m build --wheel --no-isolation --outdir backend/dist backend
```
