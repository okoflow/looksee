# Shared package

`shared` owns the strict Python contracts exchanged by the API and inference services, as
well as the model-bundle manifest schema used by both. It is a leaf package that depends
only on Pydantic and never imports application code.

Import contracts from the package root:

```python
from shared import DetectionFrame, StartStream
```

## Transport contracts

| Name | Transport | Direction |
| --- | --- | --- |
| `stream.commands` | Pub/sub | API to inference |
| `worker.events` | Pub/sub | Inference to API |
| `detection.frames` | Redis stream | Inference to API |
| `frames.last.<camera_id>` | Expiring key | Inference to API snapshot action |

Wire models reject unknown fields and are immutable after validation. `revision` fences
stale desired state, and `run_id` identifies a concrete worker run. There are no legacy
aliases or automatic schema upgrades: deploy the API and inference services together when
a shared payload changes.

See the [model catalog](../../apps/docs/content/docs/model-catalog.mdx) for the manifest
contract.
