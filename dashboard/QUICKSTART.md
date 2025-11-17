# Dashboard Quick Start

## Install Dependencies

```bash
# Backend - with uv (recommended)
uv pip install -r dashboard/requirements.txt

# Frontend
cd dashboard/frontend
npm install
cd ..
```

**Note:** The startup script auto-detects `uv` and handles installation!

**Having issues?** See `INSTALL.md` for detailed installation help.

## Run Dashboard

```bash
cd dashboard
./start.sh
```

Then open: **http://localhost:5173**

## Manual Start

**Terminal 1 - Backend:**

```bash
cd /path/to/224v-final-project
python -m uvicorn dashboard.backend.api:app --reload --port 8000
```

**Terminal 2 - Frontend:**

```bash
cd dashboard/frontend
npm run dev
```

## Features

- 📊 **View All Runs** - Browse pipeline execution history
- 🔍 **Detailed Breakdown** - Examine each of 5 pipeline steps
- ▶️ **Start New Runs** - Trigger research tasks from UI
- 🔴 **Real-Time Updates** - Watch pipeline progress live

## API Documentation

http://localhost:8000/docs

## File Structure

```
dashboard/
├── backend/        # FastAPI server
├── frontend/       # React app
├── start.sh        # Launch script
├── README.md       # Full documentation
├── USAGE.md        # Usage guide
└── requirements.txt
```

## Remove Dashboard

```bash
rm -rf dashboard/
```

---

**Need help?** See `USAGE.md` for detailed instructions.
