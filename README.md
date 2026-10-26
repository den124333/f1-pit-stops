# Do faster pit stops gain places?

I wanted to check two things. Which circuits have the slowest pit lanes, and does a faster stop at that same circuit actually gain places?

## Data

Formula 1 pit stops and lap positions, from 2012 through 25 October 2026. The tables are `pit_stops`, `lap_times`, `races` and `circuits`. I downloaded them from the [TracingInsights/RaceData](https://github.com/TracingInsights/RaceData) mirror of the Ergast data. Ergast does not host the csv zip anymore.

`duration` is the whole pit-lane time. The drive through the lane is included. It is not the two-second stop they show on TV.

The stop is written down on a lap that is only a few seconds slower than a normal lap. The slow lap is the next one, about 18 seconds slower. I count places from the lap before the stop to the end of that next lap.

## What I kept

For the pit-lane times I kept stops from 2012 on, between 12 and 50 seconds, after lap 1. I also dropped times more than 6 seconds shorter than the usual stop at that circuit. A crew cannot make the drive through the lane that much shorter. That leaves 10,770 stops from 308 races.

For the places I only kept stops where the next lap is at least 10 seconds slower than the lap before. That is 9,188 stops from 294 races. If the next lap is not clearly slower, it is usually a safety car, or the stop was on the last lap. Those stay in the pit-lane numbers, but I do not use them when I count places.

Stops are compared inside one circuit. A fast stop at Silverstone is compared with a slow stop at Silverstone, not with a stop at Monaco.

## What I found

The track decides the pit-lane time. For circuits with at least eight races, Baku is 20.7 seconds and Sochi is 30.1. Singapore is 29.7 and Silverstone is 28.9. Monaco is 25.1, around the middle. The number includes the lane, and Monaco's lane is not the longest.

A fast stop still loses places. The fastest quarter loses a median of 2 places, and 2.9 on average. The other three quarters lose a median of 3. The slowest quarter loses 3.5 on average. About 5% of the fastest stops gain a place, and about 4% of the slowest ones do. The two middle quarters are not in a clean order. So it is the fastest quarter against the rest, not one extra place for every extra second.

## What this does not show

Other cars pit on the same lap, and people retire, so the place change is not only the crew. A long time in the lane can also be a car that was held, not a slow stop.

## How to run

```powershell
py -3 -m pip install -r requirements.txt
py -3 analysis.py
```

The script downloads the four csv files into `data/ergast/` if they are not there yet. Those files are not in the git repo. Charts go to `charts/`, and the tables go to `output/`.
