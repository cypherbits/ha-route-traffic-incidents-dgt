# Route Traffic

A Home Assistant integration that tells you whether **the road you are about to
drive is closed**.

You give it an origin and a destination. It resolves the actual driving route,
then watches the official road-incident feeds and reports the incidents and
closures that fall inside that route's corridor — not the whole province, just
the roads you will actually use.

```
origin ──routing──▶ polyline ──corridor match──▶ incidents on your route
```

## Why

Existing options either give you travel time without incident data (Waze,
TomTom travel time) or incident data without knowing which road you drive
(DGT web maps). This integration joins the two: **route geometry + authoritative
incident feed**.

## Features

- **Route-aware**: only reports incidents within a configurable distance of the
  actual route polyline, so a closure 30 km away does not wake you up.
- **Provider based**: incident sources are pluggable. Ships with the Spanish
  DGT DATEX II feed.
- **Shared feed cache**: the DGT feed is several megabytes; it is downloaded
  once and shared by every configured route.
- **No API keys** for the default setup.
- **Entity names and UI translated** into English and Spanish.

## Entities

| Entity | Description |
|---|---|
| `sensor.route_closures` | Closures on the route |
| `sensor.route_incidents` | All incidents on the route |
| `sensor.route_worst_severity` | Highest severity found |
| `sensor.affected_roads` | Roads with incidents |
| `sensor.route_distance` | Route length (km) |
| `sensor.route_duration` | Estimated driving time (min) |
| `binary_sensor.route_blocked` | On when a closure affects the route |

The closure sensor exposes the full incident list in its `closures` and
`incidents` attributes, with road, cause, severity, municipality, start time
and distance from the route.

## Installation

### HACS

1. HACS → ⋮ → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Install **Route Traffic** and restart Home Assistant
4. **Settings → Devices & services → Add integration → Route Traffic**

### Manual

Copy `custom_components/route_traffic` into your `config/custom_components`
directory and restart.

## Configuration

The setup asks for two values:

| Field | Example |
|---|---|
| Origin | `zone.home` or `38.7831,0.1522` |
| Destination | `zone.work` or `device_tracker.phone` |

Both accept any entity with `latitude`/`longitude` attributes, or a literal
coordinate pair.

### Options

| Option | Default | Description |
|---|---|---|
| Corridor radius | 300 m | How far from the route an incident may be and still count |
| Update interval | 300 s | How often the corridor is checked |
| Incident providers | `dgt` | Sources of road incidents |
| Routing provider | `osrm` | Service used to resolve the route |
| OSRM server URL | `https://router.project-osrm.org` | Public demo or your own instance |

> The public OSRM demo server is rate limited and meant for light use. For
> frequent polling, self-host OSRM or point the integration at another instance.

## Automation example

```yaml
automation:
  - alias: Warn when the school run is blocked
    triggers:
      - trigger: state
        entity_id: binary_sensor.route_blocked
        to: "on"
    actions:
      - action: notify.mobile_app_phone
        data:
          title: Road closed on your route
          message: >-
            {{ state_attr('binary_sensor.route_blocked', 'closures')
               | map(attribute='road') | join(', ') }} is closed.
```

## Adding a provider

Providers live in `custom_components/route_traffic/providers/`. Implement
`IncidentProvider.async_fetch_incidents()` returning `Incident` objects and
register the class in `providers/__init__.py`.

The `Incident` model is provider agnostic, so a new source only has to map its
own payload onto it.

## Data sources

| Provider | Coverage | Key required |
|---|---|---|
| `dgt` | Spain — [NAP DATEX II](https://nap.dgt.es/) | No |

## Development

```bash
python3 tools/smoke_test.py                    # default route
python3 tools/smoke_test.py 40.4169,-3.7035 40.4065,-3.6895
```

The smoke test resolves a real route, downloads the real feed and prints how
many incidents fall inside the corridor at several radii. It needs `aiohttp`
but not Home Assistant.

## License

MIT
