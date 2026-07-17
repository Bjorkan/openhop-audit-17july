# POSSIBLE-ENHANCEMENT-010 — Possible enhancement — include frontend source and reproducible build metadata

[← Audit index](../README.md)

| Field | Value |
|---|---|
| Classification | **Possible enhancement** |
| Severity | **Enhancement** |
| Confidence | **High** |
| Area | Build and reviewability |
| Components | OpenHop Repeater Web UI |
| Audit date | 2026-07-17 |
| Status | Open in supplied snapshot |

## TL;DR

The supplied repository contains compiled/minified JavaScript assets but no corresponding Vue/TypeScript source or source maps.

## What happens now

Logical UI defects can be located by byte offset, but safe changes require editing generated one-line bundles or finding an external source snapshot.

## Expected behaviour / proposed direction

Include the frontend source tree, lockfile, build command and source maps (or documented separate source repository/revision) with releases.

## What needs to change

Enables code review, targeted patches, static typing and deterministic bundle regeneration.

## Implementation plan

The former patch sketch has been replaced with a review-oriented plan covering the required repositories/files, implementation sequence, decisions to verify, regression tests, rollout and definition of done.

[Open `implementation_plan.md`](../implementation-plans/POSSIBLE-ENHANCEMENT-010/implementation_plan.md)


## Source references and excerpts

_No single source excerpt; this is a repository/build-layout observation._
