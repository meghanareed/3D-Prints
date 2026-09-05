# profiles/

`P2S_project_settings.config` is a Bambu Studio project profile for a **Bambu Lab P2S
with a 0.4 mm nozzle**, exported from Bambu Studio 2.8 and vendored here so that the
projects `mf3.py` writes carry a real, working print profile rather than one guessed at.

It is 582 keys of Bambu's own defaults. Only two things in it are specific to this kit:

* filament slot 6 is `Bambu PLA Basic @BBL P2S - Large Flats`, which is stock Bambu PLA
  with the bed at 65 °C on the first layer and 60 °C after, instead of 55/55. Every
  object on every plate is assigned to that slot. The wall faces and the base pan lift
  at 55.
* `mf3.OVERRIDES` is applied on top when a project is written. Today that is one real
  change (`reduce_crossing_wall = 1`, for the stringing across the window openings) and
  two pinned values, so that re-exporting this file from a later Bambu Studio cannot
  quietly change the brim settings under the plates.

`docs/05_PRINT_SETTINGS.md` is generated from this file and lists everything it sets, in
printer-agnostic terms, for anyone printing on something else.

## Replacing it

Save a project from Bambu Studio, unzip it, and copy out `Metadata/project_settings.config`.
Nothing else from that project is used — `mf3.py` builds the geometry, the layout and the
per-object settings itself. It contains no account, printer-serial or network details;
this one was checked for them before it was committed.
