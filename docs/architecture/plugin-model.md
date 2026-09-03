# Plugin model

Job packs are independent distributions discovered via `importlib.metadata` entry points under `pyingestkit.jobs`. V0.1.5 accepts `JobDefinition`, `Job`, `Job` subclasses, and zero-argument factories. Discovery isolates broken plugins and keeps healthy jobs available.
