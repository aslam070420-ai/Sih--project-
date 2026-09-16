**FarmDirect — optimized app, animations preserved**

This version optimizes the supplied `Sih--project--live-price-fixed-smooth-v3.zip`.
All existing CSS files are byte-for-byte identical to the originals. Animation
keyframes, durations, easing, blur/glass styling, particle-density profiles,
canvas resolution limits, and the existing desktop/mobile/reduced-motion choices
are preserved. The dependency requirements are unchanged.

Run the app from the `farmdirect` folder:

```text
python -m pip install -r requirements.txt
python run.py
```

The original database and deployment options remain available. For an existing
local installation, use your existing `.env` and `data/farmdirect.db` with this
source. The archive contains the application source, prepared assets, tests, and
documentation; the temporary QA database is excluded.

The main changes are:

- Pointer effects now share a frame scheduler that reads element geometry before
  writing styles. Several effects on one card reuse the same measurement. Rapid
  pointer events are coalesced, and leaving a card cancels a pending hover update.
- Global pointer and scroll variables are applied to the actual effect elements
  or pseudo-elements, avoiding repeated style recalculation across the whole page.
- Cursor-aura work stops after settling below its existing display precision.
  The trail stops when its particles have faded. Both wake again on interaction;
  visibility changes and page restoration also resume the appropriate loops.
- Hero particles retain their counts, link density, resolution and motion. Distance
  rejection avoids square roots for particles that cannot connect or interact.
- Animated counters reuse their number formatter.
- NumPy, pandas and scikit-learn load on first AI use. Forecasting, pricing and
  routing use the original models and dependencies.
- Static files and the service worker skip database initialization and user lookup.
- Text assets are precompressed with gzip at build time. The server negotiates
  compressed responses while preserving correct MIME types, validators and HEAD
  requests. Versioned URLs and service-worker caches update together on a rebuild.
- Live-price DOM changes are collected into one frame. Identical responses avoid
  repeated DOM work and downstream AI-price requests. Pages with more than 16 crops
  send additional bounded batches instead of dropping the remaining crops.
- Market-status requests cannot overlap and skip automatic fetching in hidden tabs.
  Three market-cache aggregate queries are combined into one without adding stale
  data caching.

Local measurements on Windows, Python 3.14, and headless Chromium:

| Measurement | Original | Optimized | Reduction |
| --- | ---: | ---: | ---: |
| App creation, median of 5 fresh processes | 1.73 s | 0.24 s | 85.9% |
| Homepage resources, HTML excluded | 857.63 KB | 280.21 KB | 67.3% |
| Marketplace resources, HTML excluded | 775.43 KB | 261.25 KB | 66.3% |
| farmdirect-core.bundle.css, transfer size | 161.93 KB | 36.66 KB | 77.4% |
| farmdirect-core.bundle.js, transfer size | 66.43 KB | 16.54 KB | 75.1% |
| landing_i18n.js, transfer size | 84.97 KB | 21.73 KB | 74.4% |

App-creation timing includes Python imports and Flask creation; it excludes database
seeding and the first AI call. Resource measurements use the same local Flask server
setup with service workers disabled for measurement and gzip supported by the browser.
Hosting/CDN compression can change the size advantage. These are local measurements,
not a promise of a particular frame rate on every device.

In the same 120-move pointer exercise, measured browser main-thread task time fell
from 467 ms to 175 ms on the home page and from 432 ms to 198 ms on the marketplace.
These short headless traces are diagnostic rather than a device FPS benchmark.
In a two-second idle sample, the optimized marketplace and login page scheduled
zero JavaScript animation frames; their CSS animations continued. The home page
continued drawing its visible hero canvas, while empty trail/aura loops stayed idle.

Animation-preservation checks at the same desktop viewport:

| Page | CSS/WA animations, before → after | Decorative particle elements, before → after | Motion mode |
| --- | ---: | ---: | --- |
| Home | 123 → 123 | 22 → 22 | max |
| Marketplace | 117 → 117 | 18 → 18 | max |
| Login | 12 → 12 | 0 → 0 | max |

The home page retains both canvases. Phone and tablet emulation retain the original
balanced profile and 12 hero energy dots. Animation counts are snapshots after the
entry sequence; the canvas particle-count formulas are also preserved in source.

Validation completed:

- Nine Python regression tests passed, covering compressed asset integrity,
  negotiation, validators, versioning, static requests without database work,
  deferred AI imports, public pages, AI results, role dashboards, cart flow and
  market-status aggregates. The route checks also exercise forecasting, earnings,
  listing creation view, admin, IVR, checkout and logistics optimization views.
- Three Node tests passed for event coalescing, geometry reuse, read-before-write
  ordering, and cancellation when the pointer leaves.
- Browser checks passed for all 23 language choices with Hindi/English switching,
  product tilt/reset, login, Add to Cart, checkout view, IVR language/equalizer UI,
  changing and unchanged live-price responses, and a 20-crop batch.
- Browser checks passed at 390px and 768px widths for navigation, animation profile
  and horizontal overflow. Desktop and mobile screenshots were inspected.
- The service worker installed versioned assets and served the offline fallback.
- No JavaScript page errors occurred in the successful desktop/mobile browser runs.
- Python compilation and JavaScript syntax checks passed.

Tests used SQLite with temporary seeded demo data. Government market providers were
disabled only in the QA environment; changing verified-price responses were tested
with controlled fixtures. External provider availability, production PostgreSQL and
Vercel deployment were not exercised. Production provider settings in the delivered
application retain the original defaults.

Repeat the included checks from `farmdirect`:

```text
python -m unittest discover -s tests -v
node --test tests/motion_frame.test.cjs
```

The app is ready to run without an extra frontend build. After editing static source
files, rebuild the bundled script, gzip files, asset version and worker cache with:

```text
python build_assets.py
```

Then restart the Flask process so it reads the new manifest. The build uses only
Python's standard library. Node is needed only for the optional scheduler tests.
