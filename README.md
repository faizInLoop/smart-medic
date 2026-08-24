# Smart Medic

Smart Medic is a **rule-based emergency triage and waiting-queue prioritization prototype** for a small clinic. It demonstrates how patient clinical inputs can be converted into a triage level and a dynamic waiting-queue priority, with support for aging, reassessment, treatment flow, and basic operational metrics.

> **Prototype disclaimer:** *Smart Medic is an interview/demo-oriented software prototype for adult patients. It does not diagnose patients, replace clinical judgment, or represent a clinically validated medical decision-support system.*

## What the project does

A registered patient goes through the following workflow:

```text
Patient Input
    ↓
Validation
    ↓
Clinical Score
    ↓
Red-Flag Evaluation
    ↓
RED / YELLOW / GREEN Triage
    ↓
Priority Queue
    ↓
Aging / Reassessment
    ↓
Treatment
    ↓
Completed / Referred
```

The central idea is that **triage severity and queue priority are related but separate concepts**. A patient can have a moderate clinical score but still be classified as **`RED`** when a defined red-flag condition is present.

## Main features

### Rule-based triage

The prototype calculates a bounded clinical score from:

- SpO2
- Systolic blood pressure
- Respiratory rate
- Heart rate
- Consciousness
- Bleeding
- Pain level
- Age

Red flags can independently force a patient into **`RED`** triage. The application also stores the reason for a red flag so the decision can be explained in the UI.

### Dynamic waiting queue

Waiting patients are maintained in a deterministic priority queue. The queue considers:

1. Triage level (**`RED`** → **`YELLOW`** → **`GREEN`**)
2. Effective queue priority
3. Earlier arrival time
4. Patient arrival sequence / ID as a final tie-breaker

### Queue aging

Patients who remain waiting can receive an aging adjustment after the defined waiting threshold. Aging affects queue priority without changing the underlying clinical score or triage level.

### Reassessment

A waiting patient can be reassessed with updated vitals and clinical observations. The system recalculates score, red flags, triage, and queue position while preserving patient identity and arrival information.

### Deterministic treatment simulation

The interview demo uses:

- **1 treatment slot**
- **40-minute fixed simulated treatment duration**
- Automatic promotion of the highest-priority waiting patient when the slot becomes available
- No interruption of an ongoing treatment because a higher-priority patient arrives

A newly registered patient whose arrival time has already been reached is added to the queue immediately. If the treatment slot is free, the patient is automatically promoted into treatment; if the slot is occupied, the patient remains visible in the waiting queue.

The simulation clock can be advanced to reproduce queue and treatment behavior consistently during a demonstration.

### Operational metrics

The dashboard tracks:

- Average waiting time
- Average turnaround time
- Patients served
- Current waiting / treatment / completed / referred counts
- RED / YELLOW / GREEN distribution

### Patient outcomes

Completed and referred patients are retained in an outcomes view with arrival, treatment-start, and exit timestamps, plus waiting and turnaround times.

### Streamlit interface

The application provides:

- Waiting queue
- Patient registration
- Reassessment
- Treatment status
- Patient outcomes
- Patient history lookup
- Simulation time controls
- Reset functionality

## Demo and test data

The project intentionally uses two different datasets for two different purposes.

### `data/smart_medic_demo_15.csv`

A small, curated 15-patient scenario used for the **interview/demo workflow**. Its arrival times and patient conditions are selected to make queueing, reassessment, triage, and treatment behavior easy to demonstrate.

### `data/smart_medic_synthetic_150.csv`

A larger synthetic dataset used for **development, testing, and validation** across a broader range of patient conditions.

The 150-patient dataset is **not an ML training dataset**. Smart Medic is rule-based; the dataset is used to exercise and validate the rules.

### `data/smart_medic_scenario_metadata.csv`

Supporting scenario metadata used during development and debugging of the synthetic test cases.

## Project structure

```text
smart-medic/

├── app.py                        # Streamlit interview/demo application
├── run_demo.py                   # Console demonstration / compatibility demo
├── requirements.txt
├── README.md
├── .gitignore
│
├── data/
│   ├── smart_medic_demo_15.csv
│   ├── smart_medic_synthetic_150.csv
│   └── smart_medic_scenario_metadata.csv
│
├── src/
│   ├── patient.py                # Patient data model and status
│   ├── validation.py             # Input validation
│   ├── scoring.py                # Clinical score calculation
│   ├── triage.py                 # Red flags and triage classification
│   ├── queue_manager.py          # Priority queue management
│   ├── aging.py                  # Waiting-time aging
│   ├── reassessment.py           # Waiting-patient reassessment
│   ├── treatment.py              # Treatment capacity/lifecycle
│   ├── data_loader.py            # CSV loading and initialization
│   └── simulation.py             # End-to-end deterministic orchestration
│
└── tests/
    ├── test_scoring.py
    ├── test_triage.py
    ├── test_queue.py
    ├── test_aging.py
    ├── test_reassessment.py
    ├── test_treatment.py
    ├── test_data_loader.py
    └── test_simulation.py
```

## Setup

Create a virtual environment and install the project dependencies:

```bash
python -m venv .venv
```

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### macOS / Linux

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the Streamlit demo

From the project root:

```bash
python -m streamlit run app.py
```

The browser application is the primary **interview demonstration interface**.

## Run the test suite

```bash
python -m pytest -q
```

The project includes a pytest regression suite covering scoring, triage, queue behavior, aging, reassessment, treatment, data loading, simulation workflows, registration, and the Streamlit demo behavior.

## Console demonstration

The repository also contains:

```bash
python run_demo.py
```

This script is retained as a compatibility / development demonstration of the broader synthetic workflow.

## Design highlights

### Why a priority queue?

A standard FIFO queue cannot represent clinical prioritization because a newly arrived urgent patient may need to move ahead of patients who arrived earlier. The priority queue provides deterministic ordering while preserving arrival time and sequence as tie-breakers.

### Why separate clinical score and queue priority?

The clinical score represents the patient's baseline rule-based severity. Queue priority can additionally include aging so that prolonged waiting is represented without rewriting the underlying clinical assessment.

### Why reassessment?

A patient's condition can change while waiting. Reassessment allows the queue to react to new clinical observations rather than treating the original assessment as permanent.

### Why deterministic simulation?

The interview/demo mode uses a controlled simulation clock so queue movements, treatment completion, aging, and reassessment can be reproduced consistently instead of depending on real-world wall-clock timing.

## Limitations and future scope

This is a **prototype**, not a production clinical system. Important production considerations would include clinical validation, formal medical governance, audit logging, authentication/authorization, persistence, concurrency, richer patient records, configurable clinic resources, and integration with real clinical systems.

The current prototype intentionally keeps these concerns out of scope so that the core triage and queue-prioritization workflow remains small, explainable, and demonstrable.
