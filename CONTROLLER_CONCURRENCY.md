# How the controller actually runs (concurrency model)

Kopf is one Python process built on `asyncio`. This doc explains the mechanics
of how handlers get scheduled and run.

## 1. The watch stream

Kopf opens an HTTP connection per resource type it watches — e.g.
`GET /apis/trident.dev/v1/pipelineruns?watch=true`, and similarly for Pods. The
Kubernetes API server keeps this connection open and streams a JSON object down
the wire every time something changes. This is a native Kubernetes feature
(`watch=true`), not polling. Kopf reads this stream line by line.

## 2. One process, one event loop

Kopf runs inside a single Python `asyncio` event loop — one OS thread that
executes one thing at a time, but switches between many pending pieces of work
whenever the current one is waiting on I/O (a network read, an API call) instead
of blocking.

## 3. Per-object queue + task

For every distinct object Kopf sees on the watch stream (identified by
namespace + name), it keeps:

- its own internal `asyncio.Queue` of pending events for that object
- one `asyncio.Task` (a coroutine scheduled on the event loop) responsible for
  draining that queue

Example: PipelineRun `A`, PipelineRun `B`, and a build Pod each get their own
queue + task. All these tasks live on the same event loop, but since they're
mostly `await`ing I/O, the loop interleaves them — that's what "concurrent"
means here, not literal simultaneous CPU execution (Python + `asyncio` is
single-threaded).

## 4. Ordering guarantee

Within one object's task, events are pulled off that object's queue one at a
time and `await`ed to completion (including retries per Kopf's backoff config)
before the next one is taken. This is what guarantees handler code for a given
object never runs twice concurrently — no race on that object's own status.

## 5. Sync handlers vs. async handlers

- `async def handler(...)` — a coroutine. Runs directly on the event loop,
  pausing at `await` points to let other tasks run.
- `def handler(...)` (plain sync function) — calling this directly on the event
  loop would block everything else while it runs. So Kopf instead hands it to
  `loop.run_in_executor(None, handler, ...)`, which runs it on a real OS thread
  from Python's default `ThreadPoolExecutor`. The event loop `await`s that
  thread's result and keeps servicing other tasks in the meantime.

## 6. Sync client vs. kubernetes_asyncio, walked through

Whether step 5 above actually touches a thread depends entirely on which
Kubernetes client the handler body calls.

With the sync client, a `def` handler gets picked up off the object's queue and
handed to `loop.run_in_executor(thread_pool, handler, event)`. The pool gives it
an idle worker thread (or spins one up if none are free, up to its cap — around
`min(32, cpu_count+4)` by default, and threads get reused across jobs rather
than created fresh each time). That thread then runs your handler, and when it
hits something like `k8s.CoreV1Api().patch_...(...)`, the thread itself blocks
waiting on the network — not the event loop. The event loop doesn't care; it's
off servicing other objects' tasks and reading more of the watch stream in the
meantime. Once the thread's call returns, the future resolves, the `await` in
the object's task unblocks, and that task goes back for its next queued event.

With `kubernetes_asyncio`, there's no thread pool involved at all. An
`async def` handler gets `await`ed directly. When it hits
`await api.patch_namespaced_...(...)`, that's a coroutine `await`, not a blocked
thread — control just goes back to the event loop until the response arrives,
then resumes the handler exactly where it left off. Only one thread is doing
anything, ever.

That's really the whole difference: the sync client pays for its network wait by
tying up a real OS thread, while `kubernetes_asyncio` pays for it by just
parking a coroutine — cheaper, but it only works because the client itself was
written to be awaited all the way down.

Ordering doesn't change between the two. Either way, an object's task won't pull
its next queued event until the current one's `await` has returned, whether that
`await` is sitting on a thread-pool future or a plain coroutine.

## Summary

- Many coroutines, one event loop, one thread doing the scheduling.
- A small side pool of real OS threads exists only to run blocking sync handler
  code without freezing the event loop.
- Concurrency across _different_ objects comes from `asyncio` task switching;
  the _same_ object's handlers always run strictly in order.
