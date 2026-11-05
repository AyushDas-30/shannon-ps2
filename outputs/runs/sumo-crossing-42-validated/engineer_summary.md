# Road conflict screening summary

## Coverage

- Sources: sumo-crossing-42
- Track observations: 3285
- Road-user observations by group: {'pedestrian': 1903, 'vehicle': 1382}
- Unique road users: 22
- Observed time span: 139.00 seconds
- Candidate events: 2

## Ranked hotspots

1. Metric grid cell (29, 18): 2 candidate event(s); minimum indicator 1.01 s; rate per 1,000 users 90.9090909090909; main pattern vehicle_pedestrian_crossing; pair pedestrian / car; coverage flags none.

## Conflict patterns

- Other: 1
- Vehicle Pedestrian Crossing: 1

## Validation summary

- Seed/reference event count: 2
- SUMO SSM encounters available: 0
- TTC/PET agreement summary: {'TTC': None, 'PET': None}
- Seeded scenario recall: 1.0; extra candidate events: 1

## Engineering review prompts

Review crossing visibility, signal phasing, refuge provision, and approach-speed management where the mapped data and local context support it.


## Method and limitations

TTC is estimated from observed positions using a short constant-velocity prediction and buffered road-user footprints. Results are screening indicators for engineering review, not crash probabilities or legal findings.

Coordinates are assumed to be calibrated metres in one shared road-plane coordinate system. Hotspots are metric grid cells and are not yet snapped to road segments. Data gaps, detector errors, and incomplete observation coverage can hide conflicts; ‘none observed’ does not mean a location is safe.
Threshold defaults are TTC < 3 s, PET < 2 s, and DRAC > 3 m/s², following [SUMO SSM defaults](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html). Treat these as configurable screening values, not universal cutoffs.
