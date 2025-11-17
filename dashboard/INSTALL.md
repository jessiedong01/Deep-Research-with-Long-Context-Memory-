# Installation Instructions

## Option 1: Use uv (Recommended - Fast!)

If you have `uv` installed (which you do!):

```bash
# From project root
uv pip install -r dashboard/requirements.txt

# Run the dashboard
cd dashboard
./start.sh
```

The startup script will automatically detect and use `uv`!

## Option 2: Use Your Project's Virtual Environment

If you have a virtual environment at the project root (`.venv/`), activate it first:

```bash
# From project root
source .venv/bin/activate

# Install dashboard dependencies
pip install -r dashboard/requirements.txt

# Run the dashboard
cd dashboard
./start.sh
```

## Option 3: Use System Python

If your virtual environment has issues or you prefer system Python:

```bash
cd dashboard

# Install with pip
pip install -r requirements.txt

# Or with pip3
pip3 install -r requirements.txt

# Run the dashboard
./start.sh
```

## Option 4: Create a New Virtual Environment

```bash
# From project root
python3 -m venv dashboard_env
source dashboard_env/bin/activate

# Install dependencies
pip install -r dashboard/requirements.txt

# Run dashboard
cd dashboard
./start.sh
```

## Option 5: Manual Start (If Script Fails)

**Terminal 1 - Backend:**

```bash
# From project root
# With uv (recommended):
uv run uvicorn dashboard.backend.api:app --reload --port 8000

# Or with Python:
python3 -m uvicorn dashboard.backend.api:app --reload --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd dashboard/frontend
npm run dev
```

## Verify Installation

Test that dependencies are installed:

```bash
python3 -c "import fastapi, uvicorn; print('✓ Backend dependencies OK')"
```

Test the API:

```bash
# Start the backend first, then:
curl http://localhost:8000/
```

## Troubleshooting

### Issue: "No module named uvicorn"

**Solution:** Install in the correct Python environment:

```bash
# Check which python you're using
which python3

# Install there
python3 -m pip install -r dashboard/requirements.txt
```

### Issue: Virtual environment doesn't have pip

**Solution:** Recreate the virtual environment:

```bash
python3 -m venv .venv --clear
source .venv/bin/activate
pip install -r dashboard/requirements.txt
```

### Issue: Permission denied on start.sh

**Solution:**

```bash
chmod +x dashboard/start.sh
```

## Next Steps

Once installed, see `QUICKSTART.md` for usage instructions.
